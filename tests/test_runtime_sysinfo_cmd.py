import pytest
from unittest.mock import MagicMock, patch
from core.runtime import CLI, CommandCompleter

@pytest.fixture
def mock_cli_dependencies():
    with patch("core.runtime.load_config") as mock_cfg, \
         patch("core.runtime.Agent") as mock_agent, \
         patch("core.runtime.banner") as mock_banner, \
         patch("core.runtime.readline") as mock_readline:
        
        # Setup config mock
        mock_cfg.return_value = {
            "agent": {
                "provider": "ollama",
                "workspace": "workspace",
                "verbose_thinking": True,
                "auto_confirm": True
            }
        }
        mock_agent.return_value.client.provider = "ollama"
        mock_agent.return_value.client.model = "llama2"
        mock_agent.return_value.client.list_models.return_value = ["llama2"]
        yield mock_cfg, mock_agent, mock_banner, mock_readline

@patch("subprocess.run")
@patch("shutil.which")
@patch("psutil.cpu_percent")
@patch("psutil.virtual_memory")
@patch("psutil.disk_usage")
@patch("psutil.Process")
@patch("platform.system")
@patch("platform.release")
@patch("platform.machine")
@patch("platform.python_version")
def test_sysinfo_command(
    mock_py_ver, mock_mach, mock_rel, mock_sys, 
    mock_proc_class, mock_disk, mock_mem, mock_cpu,
    mock_which, mock_run,
    mock_cli_dependencies
):
    # Setup system stats mocks
    mock_sys.return_value = "Windows"
    mock_rel.return_value = "10"
    mock_mach.return_value = "AMD64"
    mock_py_ver.return_value = "3.12.1"
    
    mock_cpu.return_value = 45.2
    mock_which.return_value = None
    
    mock_virtual_mem = MagicMock()
    mock_virtual_mem.percent = 58.4
    mock_virtual_mem.used = 9280 * (1024**2)
    mock_virtual_mem.total = 16384 * (1024**2)
    mock_mem.return_value = mock_virtual_mem

    mock_disk_usage = MagicMock()
    mock_disk_usage.percent = 32.1
    mock_disk_usage.free = 128 * (1024**3)
    mock_disk_usage.total = 476 * (1024**3)
    mock_disk.return_value = mock_disk_usage

    mock_proc = MagicMock()
    mock_proc.memory_info.return_value.rss = 154 * (1024**2)
    mock_proc.create_time.return_value = 0
    mock_proc_class.return_value = mock_proc

    cli = CLI()
    
    # Asserting that handle_command does not raise exceptions
    with patch("core.runtime.logger.info") as mock_logger_info:
        cli.handle_command("/sysinfo")
        
        # Verify that dynamic dashboard section is printed
        printed_texts = [call[0][0] for call in mock_logger_info.call_args_list]
        dashboard_header_printed = any("◆ AgenticOS System Telemetry" in text for text in printed_texts)
        assert dashboard_header_printed is True
        
        # Verify platform info was printed
        platform_printed = any("Platform" in text and "Windows 10" in text for text in printed_texts)
        assert platform_printed is True

        # Verify CPU usage percent was printed
        cpu_printed = any("CPU Load" in text and "45.2%" in text for text in printed_texts)
        assert cpu_printed is True


@patch("subprocess.run")
@patch("shutil.which")
@patch("psutil.cpu_percent")
@patch("psutil.virtual_memory")
@patch("psutil.disk_usage")
@patch("psutil.Process")
@patch("platform.system")
@patch("platform.release")
@patch("platform.machine")
@patch("platform.python_version")
def test_sysinfo_command_with_gpus(
    mock_py_ver, mock_mach, mock_rel, mock_sys, 
    mock_proc_class, mock_disk, mock_mem, mock_cpu,
    mock_which, mock_run,
    mock_cli_dependencies
):
    # Setup system stats mocks
    mock_sys.return_value = "Windows"
    mock_rel.return_value = "10"
    mock_mach.return_value = "AMD64"
    mock_py_ver.return_value = "3.12.1"
    
    mock_cpu.return_value = 10.0
    mock_which.return_value = "nvidia-smi"
    
    # Mock subprocess responses for nvidia-smi and powershell
    mock_smi_res = MagicMock()
    mock_smi_res.stdout = "NVIDIA GeForce RTX 3050 6GB Laptop GPU, 100, 6144, 5.0\n"
    
    mock_ps_res = MagicMock()
    mock_ps_res.returncode = 0
    mock_ps_res.stdout = """[
        {
            "Name": "Intel(R) UHD Graphics",
            "AdapterRAM": 2147483648
        }
    ]"""
    
    def side_effect(args, **kwargs):
        if "nvidia-smi" in args[0]:
            return mock_smi_res
        elif "powershell" in args[0]:
            return mock_ps_res
        raise ValueError(f"Unexpected subprocess call: {args}")
        
    mock_run.side_effect = side_effect
    
    mock_virtual_mem = MagicMock()
    mock_virtual_mem.percent = 50.0
    mock_virtual_mem.used = 8000 * (1024**2)
    mock_virtual_mem.total = 16000 * (1024**2)
    mock_mem.return_value = mock_virtual_mem

    mock_disk_usage = MagicMock()
    mock_disk_usage.percent = 30.0
    mock_disk_usage.free = 100 * (1024**3)
    mock_disk_usage.total = 300 * (1024**3)
    mock_disk.return_value = mock_disk_usage

    mock_proc = MagicMock()
    mock_proc.memory_info.return_value.rss = 100 * (1024**2)
    mock_proc.create_time.return_value = 0
    mock_proc_class.return_value = mock_proc

    cli = CLI()
    
    with patch("core.runtime.logger.info") as mock_logger_info:
        cli.handle_command("/sysinfo")
        
        printed_texts = [call[0][0] for call in mock_logger_info.call_args_list]
        
        # Verify NVIDIA GPU printed
        nvidia_printed = any("GPU #1 Load" in text and "5.0%" in text and "NVIDIA GeForce RTX 3050" in text for text in printed_texts)
        assert nvidia_printed is True
        
        # Verify Fallback/Intel GPU printed
        intel_printed = any("GPU #2 (Aux)" in text and "Intel(R) UHD Graphics" in text and "2048MB VRAM" in text for text in printed_texts)
        assert intel_printed is True

def test_sysinfo_autocomplete(mock_cli_dependencies):
    # Verify autocompletion of /sysinfo
    _, _, _, mock_readline = mock_cli_dependencies
    completer = CommandCompleter(CLI.COMMANDS.keys(), CLI())

    mock_readline.get_line_buffer.return_value = "/sys"
    assert completer.complete("/sys", 0) == "/sysinfo"
