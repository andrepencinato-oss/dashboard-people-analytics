using System;
using System.Diagnostics;
using System.IO;

class Program {
    static void Main(string[] args) {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        string exePath = Path.Combine(dir, "OrganogramaServer.exe");
        
        if (!File.Exists(exePath)) {
            return;
        }
        
        ProcessStartInfo startInfo = new ProcessStartInfo();
        startInfo.FileName = exePath;
        startInfo.Arguments = string.Join(" ", args);
        startInfo.WindowStyle = ProcessWindowStyle.Hidden;
        startInfo.CreateNoWindow = false;
        startInfo.UseShellExecute = true;
        startInfo.WorkingDirectory = dir;
        
        try {
            Process.Start(startInfo);
        } catch (Exception) {
            // Silently fail if something goes wrong
        }
    }
}
