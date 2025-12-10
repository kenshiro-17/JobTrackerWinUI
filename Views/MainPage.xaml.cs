using System.Collections.ObjectModel;
using JobTracker.Models;
using JobTracker.Services;
using Microsoft.UI.Xaml.Controls;

namespace JobTracker.Views;

public sealed partial class MainPage : Page
{
    private readonly JobStorageService _storageService;
    private bool _isInitialized = false;
    public ObservableCollection<Job> Jobs { get; } = new();

    public MainPage()
    {
        this.InitializeComponent();
        _storageService = new JobStorageService();
        
        // Set default filter selections
        StatusFilter.SelectedIndex = 0;
        WorkModelFilter.SelectedIndex = 0;
        
        // Defer loading until page is fully loaded
        this.Loaded += MainPage_Loaded;
    }

    private void MainPage_Loaded(object sender, RoutedEventArgs e)
    {
        if (!_isInitialized)
        {
            _isInitialized = true;
            LoadJobs();
        }
    }

    private void Page_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        // Visual states handle most responsive changes automatically
        // This can be used for additional custom logic if needed
    }

    private void LoadJobs()
    {
        // Get search text from appropriate control based on visibility
        var searchQuery = FilterGrid?.Visibility == Visibility.Visible 
            ? (SearchBox?.Text ?? string.Empty)
            : (SearchBoxCompact?.Text ?? string.Empty);
            
        JobStatus? statusFilter = null;
        WorkModel? workModelFilter = null;

        // Get status filter from appropriate control
        ComboBox activeStatusFilter = FilterGrid?.Visibility == Visibility.Visible 
            ? StatusFilter 
            : StatusFilterCompact;
            
        if (activeStatusFilter?.SelectedItem is ComboBoxItem statusItem && 
            !string.IsNullOrEmpty(statusItem.Tag?.ToString()))
        {
            if (Enum.TryParse<JobStatus>(statusItem.Tag.ToString(), out var status))
            {
                statusFilter = status;
            }
        }

        // Get work model filter from appropriate control
        ComboBox activeWorkModelFilter = FilterGrid?.Visibility == Visibility.Visible 
            ? WorkModelFilter 
            : WorkModelFilterCompact;
            
        if (activeWorkModelFilter?.SelectedItem is ComboBoxItem workModelItem && 
            !string.IsNullOrEmpty(workModelItem.Tag?.ToString()))
        {
            if (Enum.TryParse<WorkModel>(workModelItem.Tag.ToString(), out var workModel))
            {
                workModelFilter = workModel;
            }
        }

        // Get filtered jobs
        var jobs = _storageService.Search(searchQuery, statusFilter, workModelFilter);

        // Update collection
        Jobs.Clear();
        foreach (var job in jobs)
        {
            Jobs.Add(job);
        }

        // Update stats
        UpdateStats();

        // Show/hide empty state
        UpdateEmptyState();
    }

    private void UpdateStats()
    {
        var stats = _storageService.GetStats();
        
        // Update wide/medium stats
        TotalCount.Text = stats.Total.ToString();
        AppliedCount.Text = stats.Applied.ToString();
        InterviewCount.Text = stats.Interview.ToString();
        OfferCount.Text = stats.Offer.ToString();
        RejectedCount.Text = stats.Rejected.ToString();
        
        // Update compact stats
        TotalCountCompact.Text = stats.Total.ToString();
        AppliedCountCompact.Text = stats.Applied.ToString();
        InterviewCountCompact.Text = stats.Interview.ToString();
        OfferCountCompact.Text = stats.Offer.ToString();
        RejectedCountCompact.Text = stats.Rejected.ToString();

        // Update subtitle
        SubtitleText.Text = stats.Total == 0 
            ? "Start tracking your job applications" 
            : $"Tracking {stats.Total} application{(stats.Total == 1 ? "" : "s")}";
    }

    private void UpdateEmptyState()
    {
        var hasJobs = Jobs.Count > 0;
        EmptyState.Visibility = hasJobs ? Visibility.Collapsed : Visibility.Visible;
        JobListView.Visibility = hasJobs ? Visibility.Visible : Visibility.Collapsed;
    }

    private async void AddJobButton_Click(object sender, RoutedEventArgs e)
    {
        await ShowJobDialog(null);
    }

    private async void SyncButton_Click(object sender, RoutedEventArgs e)
    {
        var progressText = new TextBlock { Text = "Initializing sync..." };
        var progressRing = new ProgressRing { IsActive = true, Width = 40, Height = 40 };
        
        var dialog = new ContentDialog
        {
            Title = "Syncing from Gmail",
            Content = new StackPanel
            {
                Spacing = 12,
                Children =
                {
                    progressRing,
                    progressText
                }
            },
            CloseButtonText = null,
            XamlRoot = this.XamlRoot
        };

        // Show dialog without awaiting immediately so we can run background task
        var dialogTask = dialog.ShowAsync();

        try
        {
            int addedCount = 0;
            string scriptOutput = "";
            string scriptError = "";
            
            await Task.Run(() =>
            {
                var startInfo = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "python",
                    Arguments = "gmail_job_extractor.py",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    WorkingDirectory = System.AppDomain.CurrentDomain.BaseDirectory
                };

                // Adjust working directory to project root if running from bin
                var projectRoot = Directory.GetParent(System.AppDomain.CurrentDomain.BaseDirectory)?.Parent?.Parent?.Parent?.Parent?.Parent?.FullName;
                if (projectRoot != null && File.Exists(Path.Combine(projectRoot, "gmail_job_extractor.py")))
                {
                     startInfo.WorkingDirectory = projectRoot;
                }
                 // Fallback for packaged app or direct run
                else if (File.Exists("gmail_job_extractor.py")) 
                {
                     startInfo.WorkingDirectory = Directory.GetCurrentDirectory();
                }

                using var process = System.Diagnostics.Process.Start(startInfo);
                if (process != null)
                {
                    // Read output line by line to update progress
                    var outputBuilder = new System.Text.StringBuilder();
                    var errorBuilder = new System.Text.StringBuilder();
                    
                    while (!process.StandardOutput.EndOfStream)
                    {
                        var line = process.StandardOutput.ReadLine();
                        if (line != null)
                        {
                            outputBuilder.AppendLine(line);
                            
                            // Update progress on UI thread
                            DispatcherQueue.TryEnqueue(() =>
                            {
                                // Parse progress from output
                                if (line.Contains("Found") && line.Contains("messages"))
                                {
                                    progressText.Text = line;
                                }
                                else if (line.Contains("Added:") || line.Contains("Updated Status"))
                                {
                                    addedCount++;
                                    progressText.Text = $"Processing... {addedCount} application(s) synced";
                                }
                                else if (line.Contains("Processing:") || line.Contains("Skipping"))
                                {
                                    progressText.Text = line.Length > 60 ? line.Substring(0, 60) + "..." : line;
                                }
                            });
                        }
                    }
                    
                    scriptOutput = outputBuilder.ToString();
                    scriptError = process.StandardError.ReadToEnd();
                    process.WaitForExit();

                    if (process.ExitCode != 0)
                    {
                        throw new Exception($"Script failed with exit code {process.ExitCode}:\n{scriptError}\n\nOutput:\n{scriptOutput}");
                    }
                }
            });

            dialog.Hide();
            _storageService.Reload();
            LoadJobs();
            
            var successDialog = new ContentDialog
            {
                Title = "Sync Complete",
                Content = addedCount > 0 
                    ? $"Successfully synced {addedCount} application(s)!"
                    : "Sync completed. No new applications found.",
                CloseButtonText = "OK",
                XamlRoot = this.XamlRoot
            };
            await successDialog.ShowAsync();
        }
        catch (Exception ex)
        {
            dialog.Hide();
            var errorDialog = new ContentDialog
            {
                Title = "Sync Failed",
                Content = $"Error running extractor:\n\n{ex.Message}",
                CloseButtonText = "OK",
                XamlRoot = this.XamlRoot
            };
            await errorDialog.ShowAsync();
        }
    }

    private async void EditJob_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is string jobId)
        {
            var job = _storageService.GetJob(jobId);
            if (job != null)
            {
                await ShowJobDialog(job);
            }
        }
    }

    private async void DeleteJob_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is string jobId)
        {
            var job = _storageService.GetJob(jobId);
            if (job == null) return;

            var dialog = new ContentDialog
            {
                Title = "Delete Application",
                Content = $"Delete the application for {job.Position} at {job.Company}?",
                PrimaryButtonText = "Delete",
                CloseButtonText = "Cancel",
                DefaultButton = ContentDialogButton.Close,
                XamlRoot = this.XamlRoot
            };

            var result = await dialog.ShowAsync();
            if (result == ContentDialogResult.Primary)
            {
                _storageService.DeleteJob(jobId);
                LoadJobs();
            }
        }
    }

    private void JobListView_ItemClick(object sender, ItemClickEventArgs e)
    {
        if (e.ClickedItem is Job job)
        {
            _ = ShowJobDialog(job);
        }
    }

    // Wide/Medium filter handlers
    private void SearchBox_TextChanged(object sender, TextChangedEventArgs e) { if (_isInitialized) LoadJobs(); }
    private void StatusFilter_SelectionChanged(object sender, SelectionChangedEventArgs e) { if (_isInitialized) LoadJobs(); }
    private void WorkModelFilter_SelectionChanged(object sender, SelectionChangedEventArgs e) { if (_isInitialized) LoadJobs(); }
    
    // Compact filter handlers
    private void SearchBoxCompact_TextChanged(object sender, TextChangedEventArgs e) { if (_isInitialized) LoadJobs(); }
    private void StatusFilterCompact_SelectionChanged(object sender, SelectionChangedEventArgs e) { if (_isInitialized) LoadJobs(); }
    private void WorkModelFilterCompact_SelectionChanged(object sender, SelectionChangedEventArgs e) { if (_isInitialized) LoadJobs(); }

    // Selection handlers
    private void SelectAllCheckBox_Click(object sender, RoutedEventArgs e)
    {
        if (SelectAllCheckBox.IsChecked == true)
        {
            JobListView.SelectAll();
        }
        else
        {
            JobListView.SelectedItems.Clear();
        }
    }

    private void JobListView_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        var selectedCount = JobListView.SelectedItems.Count;
        var totalCount = Jobs.Count;

        // Update selection count text
        if (selectedCount > 0)
        {
            SelectionCountText.Text = $"{selectedCount} of {totalCount} selected";
            DeleteSelectedButton.Visibility = Visibility.Visible;
        }
        else
        {
            SelectionCountText.Text = "";
            DeleteSelectedButton.Visibility = Visibility.Collapsed;
        }

        // Update Select All checkbox state
        if (selectedCount == 0)
        {
            SelectAllCheckBox.IsChecked = false;
        }
        else if (selectedCount == totalCount)
        {
            SelectAllCheckBox.IsChecked = true;
        }
        else
        {
            // Indeterminate state (some selected)
            SelectAllCheckBox.IsChecked = null;
        }
    }

    private async void DeleteSelectedButton_Click(object sender, RoutedEventArgs e)
    {
        var selectedJobs = JobListView.SelectedItems.Cast<Job>().ToList();
        if (selectedJobs.Count == 0) return;

        var dialog = new ContentDialog
        {
            Title = "Delete Selected Applications",
            Content = $"Are you sure you want to delete {selectedJobs.Count} selected application{(selectedJobs.Count == 1 ? "" : "s")}?",
            PrimaryButtonText = "Delete",
            CloseButtonText = "Cancel",
            DefaultButton = ContentDialogButton.Close,
            XamlRoot = this.XamlRoot
        };

        var result = await dialog.ShowAsync();
        if (result == ContentDialogResult.Primary)
        {
            foreach (var job in selectedJobs)
            {
                _storageService.DeleteJob(job.Id);
            }
            SelectAllCheckBox.IsChecked = false;
            LoadJobs();
        }
    }

    private async Task ShowJobDialog(Job? existingJob)
    {
        var isEdit = existingJob != null;
        var job = existingJob ?? new Job();

        // Create scrollable dialog content for small screens
        var scrollViewer = new ScrollViewer
        {
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            MaxHeight = 500
        };
        
        var panel = new StackPanel { Spacing = 12, MinWidth = 300 };
        scrollViewer.Content = panel;

        // Company
        var companyBox = new TextBox
        {
            Header = "Company *",
            PlaceholderText = "e.g. Google, Microsoft",
            Text = job.Company,
            CornerRadius = new CornerRadius(8)
        };
        panel.Children.Add(companyBox);

        // Position
        var positionBox = new TextBox
        {
            Header = "Position *",
            PlaceholderText = "e.g. Software Engineer",
            Text = job.Position,
            CornerRadius = new CornerRadius(8)
        };
        panel.Children.Add(positionBox);

        // Location
        var locationBox = new TextBox
        {
            Header = "Location",
            PlaceholderText = "e.g. San Francisco, CA",
            Text = job.Location,
            CornerRadius = new CornerRadius(8)
        };
        panel.Children.Add(locationBox);

        // Status
        var statusCombo = new ComboBox
        {
            Header = "Status",
            HorizontalAlignment = HorizontalAlignment.Stretch,
            CornerRadius = new CornerRadius(8)
        };
        foreach (var status in Enum.GetValues<JobStatus>())
        {
            statusCombo.Items.Add(new ComboBoxItem { Content = status.ToString(), Tag = status });
        }
        statusCombo.SelectedIndex = (int)job.Status;
        panel.Children.Add(statusCombo);

        // Work Model
        var workModelCombo = new ComboBox
        {
            Header = "Work Model",
            HorizontalAlignment = HorizontalAlignment.Stretch,
            CornerRadius = new CornerRadius(8)
        };
        foreach (var model in Enum.GetValues<WorkModel>())
        {
            workModelCombo.Items.Add(new ComboBoxItem { Content = model.ToString(), Tag = model });
        }
        workModelCombo.SelectedIndex = (int)job.WorkModel;
        panel.Children.Add(workModelCombo);

        // Date Applied
        var datePicker = new DatePicker
        {
            Header = "Date Applied",
            Date = job.DateApplied,
            HorizontalAlignment = HorizontalAlignment.Stretch
        };
        panel.Children.Add(datePicker);

        // Salary
        var salaryBox = new TextBox
        {
            Header = "Salary",
            PlaceholderText = "e.g. $120k - $150k",
            Text = job.Salary,
            CornerRadius = new CornerRadius(8)
        };
        panel.Children.Add(salaryBox);

        // URL
        var urlBox = new TextBox
        {
            Header = "Job URL",
            PlaceholderText = "https://...",
            Text = job.Url,
            CornerRadius = new CornerRadius(8)
        };
        panel.Children.Add(urlBox);

        // Notes
        var notesBox = new TextBox
        {
            Header = "Notes",
            PlaceholderText = "Any additional notes...",
            Text = job.Notes,
            TextWrapping = TextWrapping.Wrap,
            AcceptsReturn = true,
            Height = 80,
            CornerRadius = new CornerRadius(8)
        };
        panel.Children.Add(notesBox);

        var dialog = new ContentDialog
        {
            Title = isEdit ? "Edit Application" : "Add Application",
            Content = scrollViewer,
            PrimaryButtonText = isEdit ? "Save" : "Add",
            CloseButtonText = "Cancel",
            DefaultButton = ContentDialogButton.Primary,
            XamlRoot = this.XamlRoot
        };

        var result = await dialog.ShowAsync();

        if (result == ContentDialogResult.Primary)
        {
            // Validate required fields
            if (string.IsNullOrWhiteSpace(companyBox.Text) || string.IsNullOrWhiteSpace(positionBox.Text))
            {
                var errorDialog = new ContentDialog
                {
                    Title = "Missing Information",
                    Content = "Please enter both company name and position.",
                    CloseButtonText = "OK",
                    XamlRoot = this.XamlRoot
                };
                await errorDialog.ShowAsync();
                return;
            }

            // Update job object
            job.Company = companyBox.Text.Trim();
            job.Position = positionBox.Text.Trim();
            job.Location = locationBox.Text?.Trim() ?? string.Empty;
            job.Url = urlBox.Text?.Trim() ?? string.Empty;
            job.Salary = salaryBox.Text?.Trim() ?? string.Empty;
            job.Notes = notesBox.Text?.Trim() ?? string.Empty;

            if (statusCombo.SelectedItem is ComboBoxItem selectedStatus && selectedStatus.Tag is JobStatus status)
            {
                job.Status = status;
            }

            if (workModelCombo.SelectedItem is ComboBoxItem selectedWorkModel && selectedWorkModel.Tag is WorkModel workModel)
            {
                job.WorkModel = workModel;
            }

            job.DateApplied = datePicker.Date.DateTime;

            // Save
            if (isEdit)
            {
                _storageService.UpdateJob(job);
            }
            else
            {
                _storageService.AddJob(job);
            }

            LoadJobs();
        }
    }
}
