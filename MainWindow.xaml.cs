using Microsoft.UI;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml.Media;
using JobTracker.Views;
using WinRT.Interop;
using Windows.UI;

namespace JobTracker;

public sealed partial class MainWindow : Window
{
    private AppWindow? _appWindow;

    public MainWindow()
    {
        this.InitializeComponent();

        // Set up Mica backdrop
        SystemBackdrop = new MicaBackdrop();

        // Configure window
        ConfigureWindow();

        // Set up custom title bar
        SetupTitleBar();

        // Navigate to main page
        ContentFrame.Navigate(typeof(MainPage));
    }

    private void ConfigureWindow()
    {
        // Get the AppWindow
        var hWnd = WindowNative.GetWindowHandle(this);
        var windowId = Win32Interop.GetWindowIdFromWindow(hWnd);
        _appWindow = AppWindow.GetFromWindowId(windowId);

        if (_appWindow != null)
        {
            // Set window size
            _appWindow.Resize(new Windows.Graphics.SizeInt32(1200, 800));

            // Set minimum size and center on screen
            var displayArea = DisplayArea.GetFromWindowId(windowId, DisplayAreaFallback.Primary);
            if (displayArea != null)
            {
                var centerX = (displayArea.WorkArea.Width - 1200) / 2;
                var centerY = (displayArea.WorkArea.Height - 800) / 2;
                _appWindow.Move(new Windows.Graphics.PointInt32(centerX, centerY));
            }

            // Set title
            _appWindow.Title = "Job Tracker";
        }
    }

    private void SetupTitleBar()
    {
        // Extend content into title bar
        ExtendsContentIntoTitleBar = true;
        SetTitleBar(AppTitleBar);

        if (_appWindow != null)
        {
            // Customize title bar appearance
            var titleBar = _appWindow.TitleBar;
            
            // Make title bar buttons transparent with proper colors
            titleBar.ExtendsContentIntoTitleBar = true;
            
            // Button colors - transparent background
            titleBar.ButtonBackgroundColor = Microsoft.UI.Colors.Transparent;
            titleBar.ButtonInactiveBackgroundColor = Microsoft.UI.Colors.Transparent;
            
            // Button foreground (icon) colors
            titleBar.ButtonForegroundColor = Windows.UI.Color.FromArgb(255, 26, 26, 46); // TextPrimary
            titleBar.ButtonInactiveForegroundColor = Windows.UI.Color.FromArgb(255, 136, 136, 160); // TextMuted
            
            // Hover state
            titleBar.ButtonHoverBackgroundColor = Windows.UI.Color.FromArgb(30, 0, 0, 0);
            titleBar.ButtonHoverForegroundColor = Windows.UI.Color.FromArgb(255, 26, 26, 46);
            
            // Pressed state
            titleBar.ButtonPressedBackgroundColor = Windows.UI.Color.FromArgb(50, 0, 0, 0);
            titleBar.ButtonPressedForegroundColor = Windows.UI.Color.FromArgb(255, 26, 26, 46);
        }
    }
}
