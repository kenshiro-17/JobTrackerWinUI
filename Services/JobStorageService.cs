using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using JobTracker.Models;

namespace JobTracker.Services;

public class JobStorageService
{
    private readonly string _filePath;
    private List<Job> _jobs = new();
    private readonly JsonSerializerOptions _jsonOptions;

    public JobStorageService()
    {
        var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        var appFolder = Path.Combine(appData, "JobTracker");
        Directory.CreateDirectory(appFolder);
        _filePath = Path.Combine(appFolder, "jobs.json");
        
        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            WriteIndented = true,
            Converters = { new JsonStringEnumConverter(JsonNamingPolicy.CamelCase) }
        };
        
        Reload();
    }

    public void Reload()
    {
        try
        {
            if (File.Exists(_filePath))
            {
                var json = File.ReadAllText(_filePath);
                
                // Parse as node to handle both List (new) and Object (old) formats
                var node = JsonNode.Parse(json);
                
                if (node is JsonArray)
                {
                    _jobs = node.Deserialize<List<Job>>(_jsonOptions) ?? new List<Job>();
                }
                else if (node is JsonObject obj && obj["jobs"] is JsonArray arr)
                {
                    // Handle legacy format { "jobs": [...] }
                    _jobs = arr.Deserialize<List<Job>>(_jsonOptions) ?? new List<Job>();
                    
                    // Save in new format immediately
                    SaveJobs();
                }
                else
                {
                    _jobs = new List<Job>();
                }
            }
        }
        catch (Exception ex)
        {
            // If fails, start empty but don't overwrite file immediately to preserve data
            System.Diagnostics.Debug.WriteLine($"Error loading jobs: {ex}");
            _jobs = new List<Job>();
        }
    }

    private void SaveJobs()
    {
        try 
        {
            var json = JsonSerializer.Serialize(_jobs, _jsonOptions);
            File.WriteAllText(_filePath, json);
        }
        catch { /* Ignore save errors */ }
    }

    public List<Job> GetAllJobs() => _jobs.OrderByDescending(j => j.UpdatedAt).ToList();

    public Job? GetJob(string id) => _jobs.FirstOrDefault(j => j.Id == id);

    public void AddJob(Job job)
    {
        if (string.IsNullOrEmpty(job.Id)) job.Id = Guid.NewGuid().ToString();
        job.CreatedAt = DateTime.Now;
        job.UpdatedAt = DateTime.Now;
        _jobs.Add(job);
        SaveJobs();
    }

    public void UpdateJob(Job job)
    {
        var index = _jobs.FindIndex(j => j.Id == job.Id);
        if (index >= 0)
        {
            job.UpdatedAt = DateTime.Now;
            _jobs[index] = job;
            SaveJobs();
        }
    }

    public void DeleteJob(string id)
    {
        _jobs.RemoveAll(j => j.Id == id);
        SaveJobs();
    }

    public JobStats GetStats()
    {
        return new JobStats
        {
            Total = _jobs.Count,
            Saved = _jobs.Count(j => j.Status == JobStatus.Saved),
            Applied = _jobs.Count(j => j.Status == JobStatus.Applied),
            Interview = _jobs.Count(j => j.Status == JobStatus.Interview),
            Offer = _jobs.Count(j => j.Status == JobStatus.Offer),
            Rejected = _jobs.Count(j => j.Status == JobStatus.Rejected)
        };
    }

    public List<Job> Search(string query, JobStatus? status = null, WorkModel? workModel = null)
    {
        var results = _jobs.AsEnumerable();

        if (!string.IsNullOrWhiteSpace(query))
        {
            query = query.ToLower();
            results = results.Where(j =>
                (j.Company?.ToLower().Contains(query) ?? false) ||
                (j.Position?.ToLower().Contains(query) ?? false) ||
                (j.Location?.ToLower().Contains(query) ?? false));
        }

        if (status.HasValue)
            results = results.Where(j => j.Status == status.Value);

        if (workModel.HasValue)
            results = results.Where(j => j.WorkModel == workModel.Value);

        return results.OrderByDescending(j => j.UpdatedAt).ToList();
    }
}