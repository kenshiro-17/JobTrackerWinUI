using Microsoft.UI.Xaml.Data;
using Microsoft.UI.Xaml.Media;
using Windows.UI;
using JobTracker.Models;

namespace JobTracker.Converters;

/// <summary>
/// Converts JobStatus to a SolidColorBrush for status badges
/// </summary>
public class StatusToColorConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        if (value is JobStatus status)
        {
            return status switch
            {
                JobStatus.Saved => new SolidColorBrush(Color.FromArgb(255, 168, 213, 229)),    // PastelBlue
                JobStatus.Applied => new SolidColorBrush(Color.FromArgb(255, 181, 232, 195)),  // PastelGreen
                JobStatus.Interview => new SolidColorBrush(Color.FromArgb(255, 255, 243, 184)), // PastelYellow
                JobStatus.Offer => new SolidColorBrush(Color.FromArgb(255, 200, 230, 201)),    // Lighter green
                JobStatus.Rejected => new SolidColorBrush(Color.FromArgb(255, 245, 183, 177)), // PastelRed
                _ => new SolidColorBrush(Color.FromArgb(255, 211, 211, 211))
            };
        }
        return new SolidColorBrush(Color.FromArgb(255, 211, 211, 211));
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts WorkModel to a SolidColorBrush
/// </summary>
public class WorkModelToColorConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        if (value is WorkModel model)
        {
            return model switch
            {
                WorkModel.Remote => new SolidColorBrush(Color.FromArgb(255, 212, 197, 226)),  // PastelPurple
                WorkModel.Hybrid => new SolidColorBrush(Color.FromArgb(255, 255, 212, 168)),  // PastelOrange
                WorkModel.Onsite => new SolidColorBrush(Color.FromArgb(255, 248, 200, 220)), // PastelPink
                _ => new SolidColorBrush(Color.FromArgb(255, 211, 211, 211))
            };
        }
        return new SolidColorBrush(Color.FromArgb(255, 211, 211, 211));
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts enum values to display-friendly strings
/// </summary>
public class EnumToStringConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        if (value is Enum enumValue)
        {
            return enumValue.ToString();
        }
        return value?.ToString() ?? string.Empty;
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts DateTime to a formatted string
/// </summary>
public class DateToStringConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        if (value is DateTime date)
        {
            var format = parameter as string ?? "MMM dd, yyyy";
            return date.ToString(format);
        }
        return string.Empty;
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts boolean to Visibility
/// </summary>
public class BoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        if (value is bool boolValue)
        {
            // Check if we should invert
            var invert = parameter as string == "Invert";
            var isVisible = invert ? !boolValue : boolValue;
            return isVisible ? Visibility.Visible : Visibility.Collapsed;
        }
        return Visibility.Collapsed;
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts non-empty string to Visibility.Visible
/// </summary>
public class StringNotEmptyToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        if (value is string str)
        {
            return !string.IsNullOrWhiteSpace(str) ? Visibility.Visible : Visibility.Collapsed;
        }
        return Visibility.Collapsed;
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Returns true if collection has items
/// </summary>
public class CollectionHasItemsConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, string language)
    {
        if (value is int count)
        {
            return count > 0;
        }
        if (value is System.Collections.ICollection collection)
        {
            return collection.Count > 0;
        }
        return false;
    }

    public object ConvertBack(object value, Type targetType, object parameter, string language)
    {
        throw new NotImplementedException();
    }
}
