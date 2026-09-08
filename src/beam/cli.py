import socket                                                                                                                                     
import threading                                                                                                                                  
from pathlib import Path                                                                                                                          
from typing import Optional                                                                                                                       
                                                                                                                                                    
import click                                                                                                                                      
from rich.console import Console                                                                                                                  
from rich.prompt import Confirm                                                                                                                   
from rich.progress import (                                                                                                                       
    Progress,                                                                                                                                     
    TextColumn,                                                                                                                                   
    BarColumn,                                                                                                                                    
    DownloadColumn,                                                                                                                               
    TransferSpeedColumn,                                                                                                                          
    TimeRemainingColumn,                                                                                                                          
)                                                                                                                                                 
                                                                                                                                                    
from beam.tcp import send_file, recv_file                                                                                                         
from beam.discovery import broadcast_beacon, listen_for_beacons
from beam.web import serve_file_http

console = Console()

def format_size(num_bytes: int) -> str:
    """Format bytes into human-readable B, KB, MB, GB."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"
  

def make_progress_bar() -> Progress:
    """Create a Rich progress bar with speed and ETA."""
    return Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

@click.group()
def cli():
    """beam - Zero-config peer-to-peer file transfer"""
    pass

@cli.command()
@click.option(
    "--dir", "-d",
    type = click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=".",
    help="Directory where received file is saved (default: current directory).",
)
@click.option(
    "--port", "-p",                                                                                                                               
    type=int,                                                                                                                                     
    default=9876,                                                                                                                                 
    help="TCP port to listen on (default: 9876, or 0 for dynamic).", 
)
def recv(dir: Path, port: int):
    """Make this machine discoverable on Wi-Fi and receive a file."""
    stop_broadcasting = threading.Event()
    progress_ui = {}

    def on_port(assigned_port: int):
        console.print(f"[bold cyan]🔍 Waiting for incoming files...[/bold cyan]")                                                                 
        console.print(f"[dim]Broadcasting on Wi-Fi as '{socket.gethostname()}' (port {assigned_port})[/dim]\n")                                   
                                                                                                                                                                                                                                        
        broadcaster = threading.Thread(                                                                                                           
            target=broadcast_beacon,                                                                                                              
            kwargs={                                                                                                                              
                "beacon_data": {"device": socket.gethostname(), "port": assigned_port},                                                           
                "interval": 1.0,                                                                                                                  
                "stop_event": stop_broadcasting,                                                                                                  
            },                                                                                                                                    
            daemon=True,                                                                                                                          
        )                                                                                                                                         
        broadcaster.start()

    def confirm(metadata: dict) -> bool:
        size_str = format_size(metadata["size"])
        console.print(f"[bold yellow]📦 Incoming file offer:[/bold yellow] [bold]{metadata['filename']}[/bold] ({size_str})")
        
        accepted = Confirm.ask("Accept this file?", default=True)
        if accepted:
            stop_broadcasting.set()
            p = make_progress_bar()
            p.start()
            task = p.add_task(f"Downloading {metadata['filename']}", total=metadata["size"])
            progress_ui["progress"] = p
            progress_ui["task"] = task
            return True
        else:
            console.print("[red]❌ Transfer declined.[/red]")
            return False

    def on_progress(bytes_received: int, total_bytes: int):
            if "progress" in progress_ui:
                progress_ui["progress"].update(progress_ui["task"], completed=bytes_received)
  
    try:
        saved_path = recv_file(
            save_dir=dir,
            port=port,
            confirm_callback=confirm,
            progress_callback=on_progress,
            port_callback=on_port,
        )
        console.print(f"\n[bold green]✔ Received [white]{saved_path.name}[/white] successfully![/bold green]")
        console.print(f"[dim]Saved to: {saved_path.resolve()}[/dim]")
    except PermissionError:
        pass
    except Exception as err:
        console.print(f"\n[bold red]Error during transfer: {err}[/bold red]")
    finally:
        stop_broadcasting.set()
        if "progress" in progress_ui:
            progress_ui["progress"].stop()

@cli.command()                                                                                                                                    
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))                                                        
@click.option(                                                                                                                                    
    "--to", "-t",                                                                                                                                 
    default=None,                                                                                                                                 
    help="Direct IP address of receiver (skips discovery).",                                                                                      
)                                                                                                                                              
@click.option(                                                                                                                                    
    "--port", "-p",                                                                                                                               
    type=int,                                                                                                                                     
    default=9876,                                                                                                                                 
    help="Target port if using direct IP (default: 9876).",                                                                                       
)  
@click.option(
    "--web", "-w",
    is_flag=True,
    help="Share file via QR code for phones"
)                                                                                                                                               
def send(file_path: Path, to: Optional[str], port: int, web: bool):                                                                                          
    """Send a file to a nearby device over Wi-Fi.""" 
    file_size = file_path.stat().st_size                                                                                                          
    formatted_size = format_size(file_size)    

    
    if web:
        console.print("[bold cyan]📱 Mobile Beam Mode[/bold cyan]")
        console.print("[dim]Scan the QR code with your phone camera (must be on the same Wi-Fi):[/dim]\n")

        with make_progress_bar() as progress:
            task = progress.add_task(f"Streaming {file_path.name}", total=file_size)

            def on_progress(bytes_sent: int, total: int):
                progress.update(task, completed=bytes_sent)

            try:
                url = serve_file_http(file_path, progress_callback=on_progress)
                console.print(f"\n[dim]Direct link: {url}[/dim]")
                console.print(f"[bold green]✔ Downloaded successfully to mobile device![/bold green]")
            except Exception as err:
                console.print(f"\n[bold red]❌ Web transfer error: {err}[/bold red]")
        return                                                                                                   
                                                                                                                                                    
    console.print(f"[bold]Preparing to send:[/bold] [cyan]{file_path.name}[/cyan] ({formatted_size})\n")

    if to:
        target_host = to
        target_port = port
        console.print(f"[dim]Using direct IP: {target_host}:{target_port}[/dim]")
    else:
        with console.status("[bold cyan]Searching for nearby beam receivers on Wi-Fi...[/bold cyan]"):
            try:
                beacon, sender_ip = listen_for_beacons(timeout=30.0)
            except (TimeoutError, socket.timeout):
                console.print("[bold red]❌ No receivers found on local Wi-Fi within 30 seconds.[/bold red]")
                console.print("[dim]Make sure 'beam recv' is running on the other device.[/dim]")
                return

        target_host = sender_ip
        target_port = beacon.get("port", port)
        device_name = beacon.get("device", "Unknown device")
        console.print(f"[bold green]✔ Found receiver:[/bold green] [bold]{device_name}[/bold] ({target_host}:{target_port})\n")

    with make_progress_bar() as progress:
        task = progress.add_task(f"Sending {file_path.name}", total = file_size)

        def on_progress(bytes_sent: int, total: int):
            progress.update(task, completed=bytes_sent)

        try:
            send_file(
                host=target_host,
                port=target_port,
                file_path=file_path,
                progress_callback=on_progress,
            )
            console.print(f"\n[bold green]✔ Sent [white]{file_path.name}[/white] successfully![/bold green]")
        except PermissionError:
            console.print("\n[bold red]❌ Transfer declined by receiver.[/bold red]")
        except ConnectionError as err:
            console.print(f"\n[bold red]❌ Connection lost: {err}[/bold red]")
        except Exception as err:
            console.print(f"\n[bold red]❌ Error during transfer: {err}[/bold red]")


def main():
    cli()

if __name__ == "__main__":
    main()