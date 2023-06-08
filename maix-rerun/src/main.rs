use serialport;
use std::time::Duration;

fn main() {
    let mut port = serialport::new("/dev/ttyUSB0", 115_200)
        .timeout(Duration::from_millis(10))
        .open()
        .expect("Failed to open port");
    let output = "AT+ISP?".as_bytes();
    port.write(output).expect("Write failed!");
    let mut serial_buf: Vec<u8> = vec![0; 32];
    port.read(serial_buf.as_mut_slice())
        .expect("Found no data!");
    println!("{:?}: {}", serial_buf, String::from_utf8_lossy(&serial_buf));
}
