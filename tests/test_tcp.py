import threading                                                                                                                                  
import queue

import pytest                                                                                                                                      
from beam.tcp import send_file, recv_file                                                                                                         
                                                                                                                                                    
def test_transfer_success(tmp_path):                                                                                                                                                                                                                            
    sender_dir = tmp_path / "sender"                                                                                                              
    receiver_dir = tmp_path / "receiver"                                                                                                          
    sender_dir.mkdir()                                                                                                                            
    receiver_dir.mkdir()

    test_file = sender_dir / "sample.bin"
    content = b"Beam payload data! " * 5000 
    test_file.write_bytes(content)

    port_queue = queue.Queue()

    def run_receiver():
        recv_file(
            save_dir=receiver_dir,
            port=0,
            port_callback=lambda p: port_queue.put(p),
        )

    receiver_thread = threading.Thread(target=run_receiver)
    receiver_thread.start()

    port = port_queue.get(timeout=5)

    send_file("127.0.0.1", port, test_file)

    receiver_thread.join(timeout=5)

    received_file = receiver_dir / "sample.bin"
    assert received_file.is_file()
    assert received_file.read_bytes() == content


def test_transfer_fail(tmp_path):                                                                                                                                                                                                                            
    sender_dir = tmp_path / "sender"                                                                                                              
    receiver_dir = tmp_path / "receiver"                                                                                                          
    sender_dir.mkdir()                                                                                                                            
    receiver_dir.mkdir()

    test_file = sender_dir / "sample.bin"
    content = b"Beam payload data! " * 5000 
    test_file.write_bytes(content)

    port_queue = queue.Queue()

    def run_receiver():
        try:
            recv_file(
                save_dir=receiver_dir,
                port=0,
                confirm_callback=lambda meta: False,
                port_callback=lambda p: port_queue.put(p),
            )
        except PermissionError:
            pass

    receiver_thread = threading.Thread(target=run_receiver)
    receiver_thread.start()

    port = port_queue.get(timeout=5)

    with pytest.raises(PermissionError):
        send_file("127.0.0.1", port, test_file)

    receiver_thread.join(timeout=5)

    received_file = receiver_dir / "sample.bin"
    assert not received_file.exists()