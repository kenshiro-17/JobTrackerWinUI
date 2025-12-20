import os
# -*- coding: utf-8 -*-
import sys
import os.path
import json
import base64
import dateutil.parser
import re
import requests
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googlesearch import search

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'gmail-mcp', 'gcp-oauth.keys.json')
JOB_TRACKER_DIR = os.path.join(os.getenv('APPDATA', ''), 'JobTracker')
TOKEN_FILE = os.path.join(JOB_TRACKER_DIR, 'token.json') 
JOBS_FILE = os.path.join(JOB_TRACKER_DIR, 'jobs.json')

def get_gmail_service():
    """Shows basic usage of the Gmail API."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Credentials file not found at {CREDENTIALS_FILE}. Please configure the Gmail MCP credentials first.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def search_messages(service, query):
    """Searches for messages matching the query."""
    result = service.users().messages().list(userId='me', q=query).execute()
    messages = []
    if 'messages' in result:
        messages.extend(result['messages'])
    while 'nextPageToken' in result:
        page_token = result['nextPageToken']
        result = service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
        if 'messages' in result:
            messages.extend(result['messages'])
    return messages

def get_message_detail(service, msg_id):
    """Retrieves the details of a message."""
    message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    return message

def extract_url_from_html(html_content):
    """Extracts the first valid job link from HTML content or text."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 1. Try <a> tags first (HTML)
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text().lower()
        if any(keyword in text for keyword in ["view job", "view application", "apply now", "check status", "job description", "stelle", "bewerbung"]):
            return href
        if any(domain in href for domain in ["linkedin.com/jobs", "greenhouse.io", "lever.co", "workday.com", "personio.de", "join.com"]):
             return href
             
    # 2. Fallback: Regex for URLs in plain text
    text_content = soup.get_text(separator=' ', strip=True)
    # Regex to find http/https links
    urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*', text_content)
    
    for url in urls:
        # Check for high-priority domains in raw URLs
        if any(domain in url for domain in ["linkedin.com/jobs", "greenhouse.io", "lever.co", "workday.com", "personio.de", "join.com"]):
             return url
             
    return ""

def find_job_url(company, position):
    """Searches Google for the job posting if URL is missing."""
    search_term = position if position != "Unknown" else "careers"
    query = f'"{company}" "{search_term}" apply -"login" -"sign in"'
    print(f"  -> Searching web for: {query}")
    
    try:
        # Search for 5 results
        results = list(search(query, num_results=5, lang="en"))
        
        best_url = ""
        # Priority domains (ATS)
        priority_domains = ["greenhouse.io", "lever.co", "ashbyhq.com", "workday.com", "jobs.lev.co", "smartrecruiters.com", "personio", "join.com", "careers.", "jobs."]
        
        for url in results:
            url_str = str(url)
            
            # Skip useless results
            if any(skip in url_str.lower() for skip in ["/login", "/signin", "/search?", "glassdoor.com/job", "linkedin.com/jobs/search", "indeed.com/q-", "google.com/search"]):
                continue

            if any(pd in url_str for pd in priority_domains):
                return url_str  # Found a high-quality link
            
            # Avoid generic aggregators if possible, but keep as fallback
            if not best_url and not any(bad in url_str for bad in ["linkedin.com", "indeed.com", "glassdoor.com", "simplify.jobs"]):
                best_url = url_str
        
        return best_url if best_url else (results[0] if results else "")
        
    except Exception as e:
        print(f"  -> Search failed: {e}")
        return ""

def scrape_job_details(url):
    """Scrapes the job page for details like Position, Location, and Work Model."""
    if not url: return {}, ""
    
    print(f"Scraping URL: {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if "login" in response.url or response.status_code != 200:
            return {}, url

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=' ', strip=True).lower()
        
        details = {}
        
        # 1. Work Model - Improved detection
        work_model = "OnSite"  # Default
        
        # Count occurrences for better accuracy
        remote_count = text.count("remote") + text.count("100% remote") + text.count("fully remote") + text.count("home office") + text.count("homeoffice")
        hybrid_count = text.count("hybrid") + text.count("teilweise remote") + text.count("flexibel")
        onsite_count = text.count("on-site") + text.count("onsite") + text.count("in-office") + text.count("vor ort")
        
        # Prioritize explicit mentions
        if "100% remote" in text or "fully remote" in text or "remote only" in text:
            work_model = "Remote"
        elif "hybrid" in text or ("remote" in text and ("office" in text or "vor ort" in text)):
            work_model = "Hybrid"
        elif remote_count > hybrid_count and remote_count > onsite_count:
            work_model = "Remote"
        elif hybrid_count > 0:
            work_model = "Hybrid"
        elif onsite_count > 0:
            work_model = "OnSite"
        
        details['work_model'] = work_model

        # 2. Position (Job Title) - Enhanced extraction
        position_title = None
        
        # Method 1: JSON-LD structured data
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld and json_ld.string:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, dict) and 'title' in data:
                    position_title = data['title']
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting' and 'title' in item:
                            position_title = item['title']
                            break
            except:
                pass
        
        # Method 2: H1 tag (Most common)
        if not position_title:
            h1 = soup.find('h1')
            if h1:
                title_text = h1.get_text(separator=' ', strip=True)
                if len(title_text) < 150:  # Reasonable title length
                    position_title = title_text
        
        # Method 3: Meta properties
        if not position_title:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                position_title = og_title["content"]
        
        # Method 4: Title tag
        if not position_title:
            title_tag = soup.find("title")
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                if len(title_text) < 150:
                    position_title = title_text
        
        # Method 5: Look for class names containing "title" or "position"
        if not position_title:
            for class_name in ['job-title', 'position-title', 'role-title', 'job_title', 'position_title']:
                elem = soup.find(class_=class_name)
                if elem:
                    position_title = elem.get_text(separator=' ', strip=True)
                    if position_title and len(position_title) < 150:
                        break
                    else:
                        position_title = None
        
        # Clean up Position (Remove "Careers at...", "Job Application for...")
        if position_title and isinstance(position_title, str):
            p = position_title
            # Remove trailing company name patterns
            p = re.sub(r"(?i)\s*(?:-|at|bei|@)\s*[A-Za-z0-9\s]+$", "", p)
            p = re.sub(r"(?i)(careers?|jobs?|assignments?|application|Karriere|Stelle)\s+(at|for|bei|für)\s+.*", "", p)
            # Split by common delimiters and take first part
            p = p.split('|')[0].strip()
            p = p.split(' - ')[0].strip()
            # Remove leading/trailing punctuation
            p = p.strip('!.,;:')
            if len(p) > 3 and len(p) < 150:
                details['position'] = p

        # 3. Location - Enhanced extraction
        location = None
        
        # Method 1: Look for structured data (JSON-LD)
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld and json_ld.string:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    if 'jobLocation' in data:
                        loc_data = data['jobLocation']
                        if isinstance(loc_data, dict) and 'address' in loc_data:
                            addr = loc_data['address']
                            if isinstance(addr, dict):
                                city = addr.get('addressLocality', '')
                                country = addr.get('addressCountry', '')
                                location = f"{city}, {country}" if city and country else city or country
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            if 'jobLocation' in item:
                                loc_data = item['jobLocation']
                                if isinstance(loc_data, dict) and 'address' in loc_data:
                                    addr = loc_data['address']
                                    if isinstance(addr, dict):
                                        city = addr.get('addressLocality', '')
                                        country = addr.get('addressCountry', '')
                                        location = f"{city}, {country}" if city and country else city or country
                                        break
            except:
                pass
        
        # Method 2: Meta tags
        if not location:
            location_meta = soup.find("meta", attrs={"property": "og:location"})
            if not location_meta:
                location_meta = soup.find("meta", attrs={"name": "location"})
            if location_meta and location_meta.get("content"):
                location = location_meta["content"]
        
        # Method 3: Look for location label in HTML
        if not location:
            # Find element containing "Location" or "Standort"
            loc_patterns = [
                re.compile(r"(?:^|\s)(Location|Standort|Ort|City|Stadt)(?:\s|:|$)", re.IGNORECASE),
            ]
            for pattern in loc_patterns:
                loc_label = soup.find(string=pattern)
                if loc_label and loc_label.parent:
                    parent = loc_label.parent
                    if hasattr(parent, 'get_text'):
                        full_text = parent.get_text(separator=' ', strip=True)
                        match = re.search(r"(?:Location|Standort|Ort|City|Stadt)[:\s]+([A-Za-z0-9,\söäüß\-]+)", full_text, re.IGNORECASE)
                        if match:
                            candidate = match.group(1).strip()
                            if len(candidate) < 80 and len(candidate) > 2:
                                location = candidate
                                break
        
        # Method 4: Look for common city names in text
        if not location:
            # Common European cities (extend as needed)
            common_cities = [
                "Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart", "Düsseldorf", "München", "Köln",
                "Vienna", "Wien", "Zurich", "Zürich", "Geneva", "Genf", "Amsterdam", "Rotterdam",
                "Paris", "London", "Madrid", "Barcelona", "Milan", "Rome", "Stockholm", "Copenhagen"
            ]
            text_normal = soup.get_text(separator=' ', strip=True)
            for city in common_cities:
                if re.search(r'\b' + re.escape(city) + r'\b', text_normal, re.IGNORECASE):
                    location = city
                    break
        
        if location:
            details['location'] = location

        # 4. Notes/Summary Extraction
        notes = []
        
        # Look for "About the role" / "Requirements"
        role_headers = ["about the role", "about the job", "job description", "your tasks", "responsibilities", "aufgaben", "deine aufgaben", "über die stelle"]
        
        for header in role_headers:
             elem = soup.find(string=re.compile(header, re.IGNORECASE))
             if elem:
                 # Get next few siblings or parent's text
                 parent = elem.parent
                 if parent:
                     # Try to get the next paragraph or list
                     container = parent.next_sibling
                     # Simple heuristic: Get text of parent + next 2 siblings
                     content = parent.get_text(separator=' ', strip=True)
                     if len(content) < 100: # If header is alone
                         # try to take subsequent text
                         for _ in range(3):
                             if not container: break
                             if hasattr(container, 'get_text'):
                                 content += "\n" + container.get_text(separator=' ', strip=True)
                             container = container.next_sibling
                     
                     if len(content) > 50:
                         # Truncate
                         content = content[:500] + "..."
                         notes.append(f"{header.title()}: {content}")
                         break
        
        if not notes:
            # Fallback: First 300 chars of main text
             meta_desc = soup.find("meta", attrs={"name": "description"})
             if meta_desc and meta_desc.get("content"):
                 notes.append(meta_desc["content"][:300] + "...")
             else:
                 # Just grab first meaningful P tag
                 p_tags = soup.find_all('p')
                 for p in p_tags:
                     txt = p.get_text(strip=True)
                     if len(txt) > 100:
                         notes.append(txt[:300] + "...")
                         break
        
        if notes:
            details['notes'] = "\n".join(notes)

        return details, response.url
    except Exception as e:
        print(f"Scraping failed: {e}")
        return {}, url

def is_job_application_email(subject, body_content):
    """
    FIRST CHECK: Determines if this email is actually a job application email.
    Returns True only if job-related keywords are found in subject or body.
    """
    # Extract text from HTML if needed
    if body_content:
        soup = BeautifulSoup(body_content, "html.parser")
        text_body = soup.get_text(separator=' ', strip=True).lower()
    else:
        text_body = ""
    
    subject_lower = subject.lower()
    combined_text = (subject_lower + " " + text_body).lower()
    
    # STRICT SPAM/NON-JOB KEYWORDS - reject immediately if found
    spam_keywords = [
        "newsletter", "subscription", "webinar", "course", "sale", "discount", "promotion",
        "receipt", "order", "payment", "invoice", "verification code", "one-time password",
        "security alert", "login", "sign in", "password reset", "account", "billing",
        "rechnung", "bestellung", "zahlung", "sicherheitswarnung", "passwort", "anmelden",
        "your guide", "how to avoid", "pay your way", "starts now", "new message",
        "upcoming schedule", "shift starting", "time off request", "holiday hack",
        "delivery", "shipping", "shipped", "track your package", "paket", "versandt",
        # Travel/Ticket related (Flixbus, Train, Flight)
        "ticket", "booking", "trip", "ride", "travel", "fahrt", "buchung", "reise", 
        "passenger", "boarding", "fahrgast", "abfahrt", "arrival", "ankunft",
        # Shopping/Payments (Klarna, Paypal)
        "purchase", "statement", "buy now", "pay later", "shopp", "einkauf", "bezahlung", 
        "transaction", "transaktion", "authorized", "autorisiert", "merchant", "händler",
        # Medical/appointment related
        "termin wurde bestätigt", "appointment confirmed", "doctor", "arzt", "warten auf neuen arzt",
        "appointment request from you", "re: appointment", "ihre anfrage wurde gesendet"
    ]
    
    if any(spam_word in combined_text for spam_word in spam_keywords):
        return False
    
    # JOB APPLICATION KEYWORDS - must have at least one
    job_keywords = [
        # English keywords
        "application", "applied", "applying", "candidate", "position", "vacancy", "job offer",
        "interview", "assessment", "your application", "thank you for applying",
        "application received", "application status", "application update",
        "thank you for your interest", "joining us", "career", "recruitment",
        "your candidacy", "offer letter", "rejection", "unfortunately", "not selected",
        "received your application", "feedback on your application", "we received your",
        "update", "status", "regarding your", "employment", "hiring",
        # German keywords
        "bewerbung", "bewerben", "kandidat", "stelle", "stellenangebot",
        "vorstellungsgespräch", "assessment", "ihre bewerbung", "danke für ihre bewerbung",
        "bewerbung erhalten", "bewerbungsstatus", "bewerbungsupdate", "eingang ihrer bewerbung",
        "karriere", "rekrutierung", "absage", "leider", "nicht berücksichtigen",
        "deine bewerbung", "wir haben deine bewerbung", "status", "update"
    ]
    
    # Check if any job keyword is present
    has_job_keyword = any(keyword in combined_text for keyword in job_keywords)
    
    if not has_job_keyword:
        # Extra check: If it looks like a direct communication from a company about a status
        # but lacks explicit "application" word...
        # STRENGTHENED: We only allow this if the body contains secondary job context keywords
        # to avoid "Update on your order"
        weak_subject_triggers = ["update", "status", "regarding", "unfortunately", "leider", "absage", "rejection"]
        if any(w in subject_lower for w in weak_subject_triggers):
             # Identify secondary context in body (not just subject)
             secondary_context = ["team", "hiring", "talent", "recruiting", "career", "role", "position", "vacancy", "hr", "people", "joining", "interview", "bewerbung", "stelle", "kandidat"]
             if any(ctx in text_body for ctx in secondary_context):
                 return True
        return False
    
    return True

def parse_message(message):
    """Parses the message to extract company, position, and date."""
    headers = message['payload']['headers']
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
    date_str = next((h['value'] for h in headers if h['name'] == 'Date'), str(datetime.now()))
    
    try:
        date_applied = dateutil.parser.parse(date_str)
    except:
        date_applied = datetime.now()

    html_data = ""
    text_data = ""
    
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['mimeType'] == 'text/html' and 'data' in part['body']:
                html_data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            elif part['mimeType'] == 'text/plain' and 'data' in part['body']:
                text_data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                
    elif 'body' in message['payload'] and 'data' in message['payload']['body']:
        decoded = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8', errors='ignore')
        if message['payload'].get('mimeType') == 'text/html':
            html_data = decoded
        else:
            text_data = decoded

    # Prefer HTML, but use Text if HTML is missing
    body_content = html_data if html_data else text_data

    if not body_content:
        return None
    
    # FIRST CHECK: Is this actually a job application email?
    if not is_job_application_email(subject, body_content):
        print(f"  -> Not a job application email (no job keywords found)")
        return None

    company = "Unknown"
    position = "Unknown"
    
    # --- COMPANY EXTRACTION ---

    if "linkedin.com" in sender.lower() or "linkedin" in subject.lower():
        match = re.search(r"You applied to (.+?) at (.+)", subject, re.IGNORECASE)
        if match:
            position = match.group(1).strip()
            company = match.group(2).strip()
    
    elif "application received" in subject.lower():
         parts = subject.split('-')
         if len(parts) >= 3:
             position = parts[1].strip()
             company = parts[2].strip()

    # Pattern: "Thank you for applying to [Company]" / "Thanks for applying to..."
    # EN: "Thanks for applying to..."
    # DE: "Vielen Dank für Ihre Bewerbung bei..."
    if company == "Unknown":
        match = re.search(r"(?:Thank you|Thanks|Vielen Dank).*?for (?:your )?(?:application|apply(?:ing)?|interest|für Ihre Bewerbung).*?(?:to|in|at|bei) (.+)", subject, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip().strip('!.')
            if len(candidate) < 50:
                 company = candidate

    # Pattern: "Application Update to [Company]" / "Bewerbung bei..."
    if company == "Unknown":
        match = re.search(r"(?:Application Update|Bewerbungsupdate|Status Ihrer Bewerbung).*?(?:to|bei) (.+)", subject, re.IGNORECASE)
        if match:
             company = match.group(1).strip().strip('!.')

    # Pattern: "[Company] - [Something]" (e.g., "Flip - Unfortunately...")
    # This catches: "Flip - Unfortunately, we are unable to proceed"
    if company == "Unknown":
        match = re.search(r"^([A-Za-z0-9\s&]+?)\s*-\s*(?:Unfortunately|We regret|Thank you|Update|Status|Your application|Application|Bewerbung|Absage|Leider|Vielen Dank)", subject, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            # Verify candidate isn't a generic word
            if len(candidate) > 2 and len(candidate) < 40 and candidate.lower() not in ["application", "bewerbung", "job", "update", "status", "re", "fwd", "aw"]:
                company = candidate

    # Fallback: Try to guess from Subject if still unknown
    if company == "Unknown":
        match = re.search(r"(?:at|bei) (.+)", subject, re.IGNORECASE)
        if match:
             company = match.group(1).strip()
             # Only split on dash if it looks like "Company - Some description" (dash with spaces)
             if " - " in company or " – " in company:
                 company = re.split(r'\s+-\s+|\s+–\s+', company)[0].strip()

    # Pattern: "joining us at [Company]" (English only really)
    if company == "Unknown" and body_content:
        soup = BeautifulSoup(body_content, "html.parser")
        text_body = soup.get_text(separator=' ', strip=True)
        
        match = re.search(r"joining us at (.+?)[!.]", text_body, re.IGNORECASE)
        if match:
             company = match.group(1).strip()

    # Pattern: Signature "Sincerely, [Company]" / "Mit freundlichen Grüßen, Ihr [Company] Team"
    if company == "Unknown" and body_content:
        soup = BeautifulSoup(body_content, "html.parser")
        text_body = soup.get_text(separator=' ', strip=True)
        
        match = re.search(r"(?:Sincerely|Regards|Cheers|Grüße|Mit freundlichen Grüßen),?\s*(.+)", text_body, re.IGNORECASE)
        if match:
             candidate = match.group(1).strip()
             # Cleanup: "Your STARK Recruiting Team" -> "STARK"
             # Remove prefixes: "Ihr ", "Dein ", "Your "
             candidate = re.sub(r"(?i)^(?:Ihr|Dein|Your)\s+", "", candidate).strip()
             # Remove suffixes: "Team", "Recruiting", "Personalabteilung"
             candidate = re.sub(r"(?i)\s+(?:Recruiting|Hiring|Talent|Acquisition|People|HR|Personal|Karriere)?\s*Team.*", "", candidate).strip()
             candidate = re.sub(r"(?i)\s+(?:Recruiting|Hiring|Talent|Acquisition|People|HR|Personalabteilung)$", "", candidate).strip()
             
             if len(candidate) < 50 and len(candidate) > 2:
                 company = candidate

    # Fallback: Sender Name (Display Name)
    if company == "Unknown":
        if " <" in sender:
            display_name = sender.split(" <")[0].strip().replace('"', '')
            # Remove common suffixes (EN + DE)
            display_name = re.sub(r"(?i)\s+(?:Hiring Team|Talent Team|Recruiting|Vareers|Team|Jobs|Personalabteilung|Karriere)", "", display_name)
            if len(display_name) > 2:
                company = display_name
                print(f"  -> Extracted Company from Sender Name: {company}")

    # Fallback: Sender Domain
    if company == "Unknown":
        email_match = re.search(r'<(.+?)>', sender)
        email_addr = email_match.group(1) if email_match else sender
        
        if "@" in email_addr:
            domain = email_addr.split('@')[1].lower()
            generic_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "linkedin.com", "indeed.com", "glassdoor.com", "smartrecruiters.com", "greenhouse.io", "lever.co", "ashbyhq.com", "eu.greenhouse.io", "myworkday.com", "workday.com", "personio.de", "join.com", "googlemail.com", "protonmail.com"]
            
            if not any(gd in domain for gd in generic_domains):
                # If not a generic domain, assume it is the company domain
                # e.g. jobs@stripe.com -> Stripe
                comp_name = domain.split('.')[0].capitalize()
                
                # Basic validation: ensure it's not "bounce", "notifications", "support"
                if comp_name not in ["Bounce", "Notifications", "Support", "Info", "Hello", "Team", "Jobs", "Career", "Recruiting", "Noreply", "No-reply"]:
                    company = comp_name
                    print(f"  -> Extracted Company from Sender Domain: {company}")

    # Clean up Company Name
    company = re.sub(r'\s*\(.*?\)\s*', '', company) 
    company = company.split('<')[0].strip() 
    company = company.split('|')[0].strip() 
    company = company.rstrip('!.,')
    # Remove "Team" suffix if it's generic
    if company.lower().endswith(" team") or company.lower().endswith(" recruiting"):
        company = re.sub(r"(?i)\s+(?:Team|Recruiting|Hiring|Talent)$", "", company)
    
    # NEW: Remove "Human Resources", "Talent Acquisition"
    company = re.sub(r"(?i)\s+(?:Human Resources|Talent Acquisition|HR)$", "", company)
    
    # NEW: Remove "What happens next?" and similar status suffixes
    company = re.sub(r"(?i)[!?,.:;]\s*(?:What happens next|Application Update|Status Update|Update).*$", "", company)
    
    # NEW: Remove leading articles (Der/Die/Das)
    company = re.sub(r"^(?:Der|Die|Das|The)\s+", "", company, flags=re.IGNORECASE).strip()

    # Capitalize nicely
    if company and company.islower():
        company = company.title()

    # Clean Company punctuation
    company = company.strip("!?,.:; ")

    # --- POSITION EXTRACTION FROM SUBJECT ---
    # Pattern 1: "[Position] at [Company]"
    if position == "Unknown":
        match = re.search(r"^(.+?)\s+(?:at|bei|@)\s+.+$", subject, re.IGNORECASE)
        if match:
            candidate_pos = match.group(1).strip()
            # Remove common prefixes
            candidate_pos = re.sub(r"^(?:Application for|Bewerbung für|Your application for|Ihre Bewerbung für|Application to|Bewerbung auf)\s+", "", candidate_pos, flags=re.IGNORECASE)
            # Also reject if it's just generic phrases
            generic_phrases = ['application', 'bewerbung', 'job', 'stelle', 'your application', 'ihre bewerbung', 'deine bewerbung', 'thank you']
            if (len(candidate_pos) < 80 and len(candidate_pos) > 3 and 
                candidate_pos.lower() not in generic_phrases):
                position = candidate_pos

    # Pattern 2: "Application for [Position]" or "Bewerbung als [Position]"
    if position == "Unknown":
        # First try with dash separator (e.g., "Ihre Bewerbung als - Werkstudent")
        match = re.search(r"(?:Application for|Bewerbung für|Bewerbung als|Applied for|Beworben für|Your application for|Ihre Bewerbung für|Ihre Bewerbung als)\s*-\s*(.+?)(?:\s+at|\s+bei|$)", subject, re.IGNORECASE)
        if not match:
            # Then try without dash
            match = re.search(r"(?:Application for|Bewerbung für|Bewerbung als|Applied for|Beworben für|Your application for|Ihre Bewerbung für|Ihre Bewerbung als)\s+(.+?)(?:\s+at|\s+bei|$)", subject, re.IGNORECASE)
        
        if match:
            candidate_pos = match.group(1).strip().strip('!.,')
            # Filter out generic phrases
            if len(candidate_pos) < 80 and len(candidate_pos) > 3 and candidate_pos.lower() not in ['die position', 'the position', 'eine stelle', '']:
                position = candidate_pos
    
    # Pattern 3: "Your application as [Position]" or "Your Application - [Position]"
    # BUT NOT "Your application at [Company]" (no position in subject)
    if position == "Unknown":
        # Only match if there's "as" or dash, NOT just "at"/"bei"
        match = re.search(r"(?:Your application|Your Application|Deine Bewerbung|Ihre Bewerbung)\s+(?:as|–|−|-)\s+(.+?)(?:\s+at|\s+bei|$)", subject, re.IGNORECASE)
        if match:
            candidate_pos = match.group(1).strip().strip('!.,')
            generic_positions = ['die position', 'the position', 'a position', 'eine stelle']
            if (len(candidate_pos) < 80 and len(candidate_pos) > 3 and 
                candidate_pos.lower() not in generic_positions):
                position = candidate_pos
    
    # Pattern 3b: "[Position] - [Something]" (e.g., "Software Engineer - Job Offer")
    if position == "Unknown":
        match = re.search(r"^(?!Application|Bewerbung|Your|Ihre|Thank)(.+?)\s*-\s*(?:Application|Bewerbung|Job|Stelle|Interview|Offer|Position)", subject, re.IGNORECASE)
        if match:
            candidate_pos = match.group(1).strip()
            if len(candidate_pos) < 80 and len(candidate_pos) > 3:
                position = candidate_pos
    
    # Pattern 4: "[Company]: [Position]" 
    if position == "Unknown":
        match = re.search(r"^[^:]+:\s*(.+?)(?:\s*-|\s*\||$)", subject, re.IGNORECASE)
        if match:
            candidate_pos = match.group(1).strip()
            # Ensure it's not a generic word
            generic_words = ['application', 'bewerbung', 'job', 'stelle', 'update', 'status', 'your application', 'ihre bewerbung', 'deine bewerbung', 'thank you']
            if len(candidate_pos) < 80 and len(candidate_pos) > 3 and candidate_pos.lower() not in generic_words:
                position = candidate_pos
    
    # --- POSITION EXTRACTION FROM BODY ---
    if position == "Unknown" and body_content:
        soup = BeautifulSoup(body_content, "html.parser")
        text_body = soup.get_text(separator=' ', strip=True)
        
        # Pattern 1: "Role: Software Engineer" or "Stelle: Frontend Developer"
        match = re.search(r"(?:Role|Position|Job Title|Stelle|Jobtitel|Job):\s*([A-Za-z0-9\s\-\(\)/öäüß,&]+)", text_body, re.IGNORECASE)
        if match:
            candidate_pos = match.group(1).strip()
            # Stop at common delimiters
            candidate_pos = re.split(r'(?:Location|Standort|Department|Team|Salary|Start|Date|Reporting)', candidate_pos, flags=re.IGNORECASE)[0].strip()
            if len(candidate_pos) < 80 and len(candidate_pos) > 3:
                position = candidate_pos
        
        # Pattern 2: "your application for the [Position] role"
        if position == "Unknown":
            match = re.search(r"(?:your|their|the)\s+application\s+for\s+(?:the\s+|a\s+)?(.+?)\s+(?:role|position|stelle|job|vacancy)", text_body, re.IGNORECASE)
            if match:
                candidate_pos = match.group(1).strip()
                if len(candidate_pos) < 80 and len(candidate_pos) > 3:
                    position = candidate_pos
        
        # Pattern 2b: "You applied for [Position]" (without "role" keyword)
        if position == "Unknown":
            match = re.search(r"(?:You|Sie)\s+applied\s+(?:for|to)\s+(?:the\s+)?(.+?)(?:\s+at|\s+bei|\.|,|$)", text_body, re.IGNORECASE)
            if match:
                candidate_pos = match.group(1).strip()
                # Ensure it's not too generic
                if (len(candidate_pos) < 80 and len(candidate_pos) > 5 and 
                    not any(word in candidate_pos.lower() for word in ['application', 'position', 'job', 'company'])):
                    position = candidate_pos
        
        # Pattern 3: "for the position of [Position]"
        if position == "Unknown":
            match = re.search(r"(?:for the|für die)\s+(?:position|role|stelle|vacancy)\s+(?:of|als)\s+(.+?)(?:\.|,|at|bei|in|with)", text_body, re.IGNORECASE)
            if match:
                candidate_pos = match.group(1).strip()
                if len(candidate_pos) < 80 and len(candidate_pos) > 3:
                    position = candidate_pos
        
        # Pattern 4: "as a [Position]" or "als [Position]"
        if position == "Unknown":
            match = re.search(r"(?:as a|as an|als)\s+(.+?)(?:\s+at|\s+bei|\s+with|\s+in|\.|,|$)", text_body, re.IGNORECASE)
            if match:
                candidate_pos = match.group(1).strip()
                # Ensure it looks like a job title (contains capital letters or common job keywords)
                if (len(candidate_pos) < 80 and len(candidate_pos) > 3 and 
                    (re.search(r'[A-Z]', candidate_pos) or 
                     any(keyword in candidate_pos.lower() for keyword in ['engineer', 'developer', 'manager', 'analyst', 'designer', 'specialist', 'consultant', 'architekt', 'ingenieur']))):
                    position = candidate_pos
        
        # Pattern 5: "You applied to [Position]" (LinkedIn style)
        if position == "Unknown":
            match = re.search(r"You applied to\s+(.+?)\s+at", text_body, re.IGNORECASE)
            if match:
                candidate_pos = match.group(1).strip()
                if len(candidate_pos) < 80 and len(candidate_pos) > 3:
                    position = candidate_pos
        
        # Pattern 6: "interesse an der Stelle als [Position]" (German)
        if position == "Unknown":
            match = re.search(r"(?:interesse an|Bewerbung auf|interest in).*?(?:der Stelle als|die Position|the position of|the role of)\s+(.+?)(?:\.|,|bei|at|$)", text_body, re.IGNORECASE)
            if match:
                candidate_pos = match.group(1).strip()
                if len(candidate_pos) < 80 and len(candidate_pos) > 3:
                    position = candidate_pos

    # Status Detection
    status = "Applied"
    
    # 1. Subject-based Rejection Detection (Strong Signal)
    if any(phrase in subject.lower() for phrase in ["rejected", "declined", "not selected", "unfortunately", "absage", "nicht berücksichtigt", "nicht weiter"]):
        status = "Rejected"
    
    # 2. Body-based Rejection Detection
    elif body_content:
        soup_status = BeautifulSoup(body_content, "html.parser")
        text_status = soup_status.get_text(separator=' ', strip=True).lower()
        
        # Check EN and DE rejection phrases
        rejection_phrases = [
        # English phrases
        "not able to move forward", "unfortunately", "not be proceeding", "decided to pursue other", "not selected",
        "thank you for your interest", "best of luck", "future endeavors", "other candidates", "regret to inform", "careful consideration",
        "position has been closed", "role has been filled", "not advancing", "not proceeding",
        "move forward with another candidate", "high volume of applications", "keep your application on file", 
        "won't be moving forward", "at this time", "went with another candidate", "chose another candidate",
        # German phrases
        "leider", "nicht berücksichtigen", "absage", "absagen", "anderweitig", "nicht weiterverfolgen",
        "mit bedauern", "keine positive nachricht", "entscheidung gefallen", "nicht in die engere wahl",
        "kein angebot", "wünschen ihnen alles gute", "keine ruckmeldung", "keine antwort", "keine position", "leider können wir", "nicht für die position geeignet",
        "andere kandidaten", "kandidat", "anderweitig besetzt", "viel erfolg", "leider keine positive rückmeldung", "bedauern"
        ]
        
        # Check subject for rejection cues
        if any(phrase in subject.lower() for phrase in ["status update", "bewerbungsstatus", "update on your application", "regarding your application"]):
            # If subject suggests an update, be more sensitive to body keywords
            if any(phrase in text_status for phrase in rejection_phrases):
                status = "Rejected"
        elif any(phrase in text_status for phrase in rejection_phrases):
            # Double check strict negative context to avoid "Unfortunately I am busy" (unlikely from company)
            # Broadened strict list (include German equivalents)
            if any(strict in text_status for strict in ["not able to move forward", "not be proceeding", "regret to inform", "leider", "nicht berücksichtigen", "absage", "other candidates", "keine positive nachricht", "andere kandidaten", "kandidat", "position has been closed", "move forward", "not advancing", "went with another", "anderweitig", "won't be moving forward", "chose another"]):
                status = "Rejected"

    job_url = extract_url_from_html(body_content)
    
    # Extract Location from email body
    location = "Unknown"
    if body_content:
        soup_loc = BeautifulSoup(body_content, "html.parser")
        text_body_loc = soup_loc.get_text(separator=' ', strip=True)
        
        # Pattern 1: "Location: Berlin" or "Standort: München"
        match = re.search(r"(?:Location|Standort|Ort|Office Location|Work Location):\s*([A-Za-zäöüßÄÖÜ\s,\-]+?)(?:\n|<|$|\||;|Work Model|Remote|Hybrid|OnSite|Department|Team)", text_body_loc, re.IGNORECASE)
        if match:
            candidate_loc = match.group(1).strip()
            if len(candidate_loc) < 50 and len(candidate_loc) > 2:
                location = candidate_loc
        
        # Pattern 2: Look for common city names
        if location == "Unknown":
            common_cities = [
                "Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart", "Düsseldorf", "München", "Köln",
                "Vienna", "Wien", "Zurich", "Zürich", "Geneva", "Genf", "Amsterdam", "Rotterdam",
                "Paris", "London", "Madrid", "Barcelona", "Milan", "Rome", "Stockholm", "Copenhagen", "Brussels"
            ]
            for city in common_cities:
                if re.search(r'\b' + re.escape(city) + r'\b', text_body_loc, re.IGNORECASE):
                    location = city
                    break
    
    # Extract Work Model from email body
    work_model = "OnSite"  # Default
    if body_content:
        soup_wm = BeautifulSoup(body_content, "html.parser")
        text_body_wm = soup_wm.get_text(separator=' ', strip=True).lower()
        
        # Count occurrences of work model keywords
        remote_count = text_body_wm.count("remote") + text_body_wm.count("100% remote") + text_body_wm.count("fully remote") + text_body_wm.count("home office") + text_body_wm.count("homeoffice")
        hybrid_count = text_body_wm.count("hybrid") + text_body_wm.count("teilweise remote") + text_body_wm.count("flexibel")
        onsite_count = text_body_wm.count("on-site") + text_body_wm.count("onsite") + text_body_wm.count("in-office") + text_body_wm.count("vor ort")
        
        # Determine work model based on keyword frequency
        if "100% remote" in text_body_wm or "fully remote" in text_body_wm or "remote only" in text_body_wm:
            work_model = "Remote"
        elif "hybrid" in text_body_wm or ("remote" in text_body_wm and ("office" in text_body_wm or "vor ort" in text_body_wm)):
            work_model = "Hybrid"
        elif remote_count > hybrid_count and remote_count > onsite_count and remote_count > 0:
            work_model = "Remote"
        elif hybrid_count > 0:
            work_model = "Hybrid"
        elif onsite_count > 0:
            work_model = "OnSite"

    # Final Clean of Position
    if position and position != "Unknown":
        # Remove zero-width spaces and invisible chars
        position = position.replace('\u200b', '').replace('\ufeff', '').strip()
        # Remove trailing " | Company"
        if company != "Unknown":
             position = re.split(r'\s*\|\s*' + re.escape(company), position, flags=re.IGNORECASE)[0].strip()
        
        # Reject if just "Work" or single generic word
        if position.lower() in ["work", "job", "position"]:
             position = "Unknown"

    return {
        "company": company,
        "position": position,
        "date_applied": date_applied.isoformat(),
        "url": job_url,
        "status": status,
        "work_model": work_model, 
        "location": location,
        "notes": f"Auto-extracted from Gmail. Subject: {subject}"
    }

def is_valid_job(job, allow_unknown_position=False):
    """Checks if the extracted job looks valid (not gibberish)."""
    company = job['company']
    position = job['position']
    
    # Check 1: Company Name Validity
    if len(company) < 3 or len(company) > 40:
        print(f"  -> Invalid Company Length: {company}")
        return False

    # Check 0: Date Validity (Strict 30 days & 2026+)
    try:
        if 'date_applied' in job:
            job_date = dateutil.parser.parse(job['date_applied'])
            # Ensure timezone awareness compatibility (naive vs aware)
            now = datetime.now(job_date.tzinfo) 
            
            # 1. Reject if older than 30 days
            if (now - job_date).days > 30:
                 print(f"  -> Invalid Date (Older than 30 days): {job['date_applied']}")
                 return False
            
            # 2. Reject if before 2026
            if job_date.year < 2026:
                 print(f"  -> Invalid Date (Before 2026): {job['date_applied']}")
                 return False
    except Exception as e:
        print(f"  -> Date validation check failed: {e}")
        # Be safe, dont reject on parse error unless we want strict
        pass
    
    # Blacklist User Name and Generics
    invalid_companies = ["Notification", "Support", "Team", "Unknown", "Reply", "No-Reply", "Mail", "Info", "Bewerbung", "Karriere", 
                         "Rahul", "Raj", "Pallathuparambil", "Rahul Raj", "Rahul Raj Pallathuparambil", "Rahul Raj P",
                         "TeleClinic", "Ext", "Elektronisches Postfach", "Sparkasse", "Elektronisches Postfach Ihrer Sparkasse",
                         "Bank", "Banking", "Postfach", "The", "A", "An"]
    # Case-insensitive check
    if any(company.lower() == inv.lower() for inv in invalid_companies):
        print(f"  -> Invalid Company Name (Blacklisted): {company}")
        return False
    
    # Check for bank/financial keywords in company name
    if any(keyword in company.lower() for keyword in ["sparkasse", "postfach", "elektronisches postfach", "bank notification"]):
        print(f"  -> Invalid Company (Bank/Notification): {company}")
        return False

    # Check 2: Position Validity
    # STRICT MODE: If Position is "Unknown", REJECT IT (unless allowed temporarily).
    if not allow_unknown_position and position == "Unknown":
         print(f"  -> Invalid Position (Unknown): {company}")
         return False

    # Reject "None" or "Null" strings in position
    if position.lower() in ["none", "null", "undefined"]:
         print(f"  -> Invalid Position (Null value): {company}")
         return False

    # Logic: Titles are rarely longer than 10 words unless it's a sentence
    if len(position.split()) > 10:
         print(f"  -> Invalid Position (Looks like a description): {position}")
         return False

    # Logic: Position identical to company is usually a parsing error (e.g. "Google" at "Google")
    if position.lower() == company.lower():
         print(f"  -> Invalid Position (Same as Company): {position}")
         return False

    if len(position) > 80:
         print(f"  -> Invalid Position Length (Too long): {position}")
         return False
    
    # Check 3: Reject generic/meaningless positions
    invalid_positions = [
        "ihre bewerbung", "deine bewerbung", "your application", "application", 
        "bewerbung", "thank you for your application", "we received your application",
        "we received your application for a position", "wir haben deine bewerbung", 
        "eingang ihrer bewerbung", "application received", "thank you", "danke", 
        "feedback on your application", "update on your application",
        "your application has entered", "technical subdomain", "mission logged",
        "stretch every bank holiday", "pay your way", "appointment request", 
        "warten auf neuen arzt", "in in berlin", "neue nachrichten",
        "neue nachrichten in ihrem elektronischen postfach",
        # New junk phrases detected in test
        "danke für deine bewerbung", "vielen dank für deine bewerbung", 
        "vielen dank für ihre bewerbung", "danke für dein interesse",
        "vielen dank für deine bewerbung und dein"
    ]
    
    position_lower = position.lower().strip()
    if position_lower in invalid_positions:
        print(f"  -> Invalid Position (Too generic): {position}")
        return False
    
    # Check if position is just a fragment like "in in Berlin"
    if position_lower.startswith("in in ") or position_lower.endswith(" in in"):
        print(f"  -> Invalid Position (Malformed): {position}")
        return False
        
    # Check for "Thank you" starts
    if position_lower.startswith("vielen dank") or position_lower.startswith("danke für") or position_lower.startswith("thank you"):
        print(f"  -> Invalid Position (Sentence): {position}")
        return False

    # Check 4: Gibberish/Spam Detect
    if "receipt" in position.lower() or "invoice" in position.lower():
        return False

    return True

def load_jobs():
    if not os.path.exists(JOBS_FILE):
        return []
    try:
        with open(JOBS_FILE, 'r') as f:
            content = f.read()
            if not content: return []
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'jobs' in data:
                return data['jobs']
            return []
    except Exception as e:
        print(f"Error loading jobs: {e}")
        return []

def save_jobs(jobs):
    try:
        if not os.path.exists(JOB_TRACKER_DIR):
            os.makedirs(JOB_TRACKER_DIR)
        with open(JOBS_FILE, 'w') as f:
            json.dump(jobs, f, indent=4)
        print("Jobs saved successfully.")
    except Exception as e:
        print(f"Error saving jobs: {e}")

def process_job_update(jobs, new_job_data):
    """Adds a new job or updates an existing one with new status/notes."""
    
    # Validation Check - Allow Unknown position initially (we will try to scrape it)
    if not is_valid_job(new_job_data, allow_unknown_position=True):
        return False

    # 1. Identify specific status from this email
    current_status_from_email = new_job_data.get('status', 'Applied')
    subject_lower = new_job_data['notes'].lower()
    
    # Heuristics for Interview/Test (EN/DE)
    interview_keywords = [
        "interview", "schedule a call", "availability", "booking", "meet the team", "coding challenge", "assessment", "hackerrank", "codesignal", "take-home", "assignment", "test",
        "vorstellungsgespräch", "termin", "einladung", "kennenlernen", "online assessment", "video-interview"
    ]
    
    # Priority: Rejected > Interview > Offer > Applied
    # If explicitly rejected, override interview detection
    if current_status_from_email != "Rejected":
        if any(k in subject_lower for k in interview_keywords):
            current_status_from_email = "Interview"
    
    # 2. Find existing job
    existing_job = None
    for job in jobs:
        # Match on Company Name (case-insensitive) - support both capitalized and lowercase keys
        job_company = job.get('Company', job.get('company', '')).lower()
        if job_company == new_job_data['company'].lower():
             # Strict match on Position OR if one of them is "Unknown"
             p1 = job.get('Position', job.get('position', '')).lower()
             p2 = new_job_data['position'].lower()
             
             # Strict equality only. Do NOT use substring match to avoid merging different roles.
             if p1 == p2 or p1 == "unknown" or p2 == "unknown":
                existing_job = job
                break
    
    if existing_job:
        # UPDATE EXISTING
        updated = False
        old_status = existing_job.get('Status', existing_job.get('status', 'Saved'))
        
        # Always allow update TO Rejected
        if current_status_from_email == "Rejected" and old_status != "Rejected":
            existing_job['Status'] = "Rejected"
            updated = True
            print(f"  -> Updated Status to REJECTED: {existing_job.get('Company', existing_job.get('company', 'Unknown'))}")
            
        elif current_status_from_email == "Interview":
            if old_status in ["Saved", "Applied"]:
                existing_job['Status'] = "Interview"
                updated = True
                print(f"  -> Updated Status to INTERVIEW: {existing_job.get('Company', existing_job.get('company', 'Unknown'))}")
        
                print(f"  -> Updated Status to INTERVIEW: {existing_job.get('Company', existing_job.get('company', 'Unknown'))}")
        
        # Merge missing data fields
        # 1. URL
        if new_job_data.get('url') and not existing_job.get('Url', existing_job.get('url')):
            existing_job['Url'] = new_job_data['url']
            updated = True
        
        # 2. Location (Update if existing is Unknown/Empty/Blank and new is valid)
        old_loc = existing_job.get('Location', existing_job.get('location', ''))
        new_loc = new_job_data.get('location', 'Unknown')
        if (not old_loc or old_loc == "Unknown") and new_loc != "Unknown":
            existing_job['Location'] = new_loc
            updated = True
            print(f"  -> Merged Location: {new_loc}")
            
        # 3. Work Model (Update if existing is default OnSite and new is different, or if existing is missing)
        old_wm = existing_job.get('WorkModel', existing_job.get('work_model', ''))
        new_wm = new_job_data.get('work_model', 'OnSite')
        if not old_wm or (old_wm == "OnSite" and new_wm != "OnSite"):
            existing_job['WorkModel'] = new_wm
            updated = True
            print(f"  -> Merged Work Model: {new_wm}")

        # Append Note
        notes_key = 'Notes' if 'Notes' in existing_job else 'notes'
        if new_job_data['notes'] not in existing_job.get(notes_key, ''):
            date_str = datetime.now().strftime("%Y-%m-%d")
            existing_job[notes_key] = (existing_job.get(notes_key, '') + f"\n[{date_str}] New Email: {new_job_data['notes'].replace('Auto-extracted from Gmail. ', '')}").strip()
            existing_job['UpdatedAt'] = datetime.now().isoformat()
            updated = True
            
        if updated:
            return True 
        else:
            print(f"Skipping duplicate/no-change: {new_job_data['company']}")
            return False

    else:
        # CREATE NEW
        # Web Search for missing URL
        if not new_job_data['url']:
            print(f"URL missing for {new_job_data['company']}. searching web...")
            found_url = find_job_url(new_job_data['company'], new_job_data['position'])
            if found_url:
                print(f"  -> Found URL: {found_url}")
                new_job_data['url'] = found_url
                time.sleep(2) # Polite delay
        
        # Scrape for details (Location, Position fallback, Work Model, Notes)
        if new_job_data['url']:
            details, final_url = scrape_job_details(new_job_data['url'])
            if 'work_model' in details:
                new_job_data['work_model'] = details['work_model']
                print(f"  -> Found Work Model: {new_job_data['work_model']}")
            
            # Use scraped position if extraction was poor ("Unknown")
            if 'position' in details and (new_job_data['position'] == "Unknown" or len(new_job_data['position']) < 5):
                new_job_data['position'] = details['position']
                print(f"  -> Found Position from URL: {new_job_data['position']}")

            if 'location' in details:
                 new_job_data['location'] = details['location']
                 print(f"  -> Found Location: {new_job_data['location']}")

            if 'notes' in details and details['notes']:
                new_job_data['notes'] += f"\n\n[Job Post Summary]\n{details['notes']}"

            if final_url:
                new_job_data['url'] = final_url
        
        # Last resort: Try to extract position from URL path
        if new_job_data['position'] == "Unknown" and new_job_data['url']:
            try:
                from urllib.parse import urlparse, unquote
                parsed_url = urlparse(new_job_data['url'])
                path = unquote(parsed_url.path)
                # Look for job title patterns in URL like "/jobs/software-engineer" or "/careers/data-analyst"
                match = re.search(r'/(?:jobs|careers|positions|stellenangebote)/([a-zA-Z0-9\-_]+)', path, re.IGNORECASE)
                if match:
                    slug = match.group(1).replace('-', ' ').replace('_', ' ').title()
                    # Filter out generic terms
                    if len(slug) > 5 and slug.lower() not in ['apply', 'application', 'view', 'details']:
                        new_job_data['position'] = slug
                        print(f"  -> Extracted Position from URL: {slug}")
            except:
                pass
        
        # Final validation before adding - Allow Unknown position if company is legitimate
        if not is_valid_job(new_job_data, allow_unknown_position=True):
             return False

        if current_status_from_email != "Applied":
             new_job_data['status'] = current_status_from_email

        import uuid
        # If position is Unknown, use a placeholder that's more user-friendly
        position_display = new_job_data['position'] if new_job_data['position'] != "Unknown" else "(Position not specified in email)"
        
        job_entry = {
            "Id": str(uuid.uuid4()),
            "Company": new_job_data['company'],
            "Position": position_display,
            "Location": new_job_data.get('location', 'Unknown'),
            "WorkModel": new_job_data['work_model'], 
            "Status": new_job_data['status'],
            "DateApplied": new_job_data['date_applied'],
            "Url": new_job_data['url'],
            "Salary": "",
            "Notes": new_job_data['notes'],
            "CreatedAt": datetime.now().isoformat(),
            "UpdatedAt": datetime.now().isoformat()
        }
        jobs.append(job_entry)
        print(f"Added: {new_job_data['company']} - {new_job_data['position']} [{new_job_data['status']}]")
        return True

def main():
    import sys
    try:
        print("Starting Gmail job extraction...", flush=True)
        service = get_gmail_service()
        print("Gmail service authenticated successfully.", flush=True)
        
        jobs = load_jobs()
        print(f"Loaded {len(jobs)} existing jobs from storage.", flush=True)

        # 1. Base Query: Standard broad search for new applications
        # 1. Base Query: Standard broad search for new applications
        base_query = 'after:2025/12/31 (subject:application OR subject:bewerbung OR subject:applied OR subject:candidate OR subject:assessment OR subject:interview OR subject:rejection OR subject:offer OR subject:vacancy OR subject:role OR subject:position OR subject:apply OR subject:thanks OR subject:update OR subject:status OR from:noreply OR from:jobs OR from:career OR from:recruiting OR from:talent)'
        
        # 2. Company Query: Specifically check emails from companies we've already applied to
        # This helps catch "Update on your application" emails that might miss the broad keywords
        company_query_parts = []
        if jobs:
            existing_companies = set()
            for job in jobs:
                comp = job.get('Company', job.get('company', '')).strip()
                if comp and comp != "Unknown" and len(comp) > 2:
                    # Escape quotes in company names
                    safe_comp = comp.replace('"', '\\"')
                    existing_companies.add(f'"{safe_comp}"')
            
            # Limit to avoid query length errrors (approx 50 most recent/relevant)
            # For now, take first 50 unique companies
            target_companies = list(existing_companies)[:50]
            if target_companies:
                company_query_parts = [f'subject:{c}' for c in target_companies]
        
        # Combine queries
        # query = base_query OR (newer_than:60d AND (subject:"Company A" OR subject:"Company B"...))
        # We look back further (60d) for existing companies to catch late rejections
        final_query = base_query
        
        if company_query_parts:
            companies_str = " OR ".join(company_query_parts)
            secondary_query = f'after:2025/12/31 ({companies_str})'
            final_query = f'{{ {base_query} {secondary_query} }}'
            print(f"Added targeted search for {len(company_query_parts)} existing companies.", flush=True)

        print(f"Searching Gmail...", flush=True)
        
        messages = search_messages(service, final_query)
        
        # Deduplicate messages by ID (since OR query might return duplicates)
        unique_messages = {msg['id']: msg for msg in messages}.values()
        messages = list(unique_messages)
        
        print(f"Found {len(messages)} messages.", flush=True)
        
        if len(messages) == 0:
            print("No messages found. Try increasing the time range or checking your Gmail filters.", flush=True)
            return
        
        added_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        print(f"Fetching {len(messages)} messages using Batch API...", flush=True)
        
        # Helper to process batch responses
        def batch_callback(request_id, response, exception):
            nonlocal added_count, updated_count, skipped_count, error_count
            if exception:
                error_count += 1
                print(f"Error fetching message {request_id}: {exception}", flush=True)
            else:
                try:
                    detail = response
                    parsed = parse_message(detail)
                    
                    if parsed:
                        # Relaxed check: Allow Unknown company if Position is known
                        if parsed['company'] == "Unknown" and parsed['position'] != "Unknown":
                            # Check if position is "too generic" to stand on its own without a company name
                            generic_positions = ["update", "status", "job", "application", "bewerbung", "offer", "vacancy", "role", "position", "hi"]
                            if parsed['position'].lower() not in generic_positions:
                                parsed['company'] = "Unknown Company"
                                print(f"  -> Warning: Company Unknown for position '{parsed['position']}'. Saving as 'Unknown Company'.", flush=True)
                            else:
                                print(f"  -> Rejected: Company Unknown and Position '{parsed['position']}' is too generic.", flush=True)

                        if parsed['company'] != "Unknown":
                            result = process_job_update(jobs, parsed)
                            if result:
                                # We fix counting logic slightly or just aggregate total "Actions"
                                updated_count += 1 
                            else:
                                skipped_count += 1
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"Error processing message {request_id}: {e}", flush=True)

        # Process in chunks of 25 to vary polite and avoid Rate Limit (429)
        chunk_size = 25
        for i in range(0, len(messages), chunk_size):
            chunk = messages[i:i + chunk_size]
            batch = service.new_batch_http_request(callback=batch_callback)
            
            for msg in chunk:
                req = service.users().messages().get(userId='me', id=msg['id'], format='full')
                batch.add(req, request_id=msg['id'])
            
            print(f"Executing batch {i // chunk_size + 1}/{(len(messages) + chunk_size - 1) // chunk_size}...", flush=True)
            try:
                batch.execute()
                time.sleep(1) # Polite delay between batches
            except Exception as e:
                print(f"Batch execution failed: {e}", flush=True)
            except Exception as e:
                print(f"Batch execution failed: {e}", flush=True)
                error_count += len(chunk)

        # Recalculate counts based on list size changes is tricky if we don't track it.
        # But 'updated_count' above is incremented for both adds and updates.
        # Let's just report "Processed Actions" 

        
        # Always save jobs if there were any updates
        if added_count > 0 or updated_count > 0:
            print(f"\nSaving {len(jobs)} jobs to storage...", flush=True)
            save_jobs(jobs)
            print(f"\n✓ Successfully synced!", flush=True)
            print(f"  - Added: {added_count}", flush=True)
            print(f"  - Updated: {updated_count}", flush=True)
            print(f"  - Skipped: {skipped_count}", flush=True)
            if error_count > 0:
                print(f"  - Errors: {error_count}", flush=True)
        else:
            print("\n✓ Sync completed. No new or updated applications found.", flush=True)
            print(f"  - Skipped: {skipped_count}", flush=True)
            if error_count > 0:
                print(f"  - Errors: {error_count}", flush=True)
            
    except Exception as e:
        print(f"FATAL ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
