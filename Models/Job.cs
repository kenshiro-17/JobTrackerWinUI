using System.Text.Json.Serialization;

namespace JobTracker.Models;

public enum JobStatus
{
    Saved,
    Applied,
    Interview,
    Offer,
    Rejected
}

public enum WorkModel
{
    Remote,
    Hybrid,
    Onsite
}

public class Job
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Company { get; set; } = string.Empty;
    public string Position { get; set; } = string.Empty;
    public string Location { get; set; } = string.Empty;
    public WorkModel WorkModel { get; set; } = WorkModel.Remote;
    public JobStatus Status { get; set; } = JobStatus.Saved;
    public DateTime DateApplied { get; set; } = DateTime.Now;
    public string Url { get; set; } = string.Empty;
    public string Salary { get; set; } = string.Empty;
    public string Notes { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.Now;
    public DateTime UpdatedAt { get; set; } = DateTime.Now;
}

public class JobStats
{
    public int Total { get; set; }
    public int Saved { get; set; }
    public int Applied { get; set; }
    public int Interview { get; set; }
    public int Offer { get; set; }
    public int Rejected { get; set; }
}
