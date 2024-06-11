
## import 
import threading
import unreliable_channel
import zlib
import sys
import socket
from collections import deque


## define and initialize
packet_header = []
expect_number = 0
recv_addr = ("", 0)
output_file = sys.argv[2]
log_file = sys.argv[3]
ack_queue = deque()

lock = threading.Lock()

class PacketHeader:
	def __init__(self, type = 1, seqNum = 0, length = 0, checksum = 0):
		self.type = type
		self.seqNum = seqNum
		self.length = length
		self.checksum = checksum

def create_packet(seq_number, length):
# create data packet
# crc32 available through zlib library
	MTP_header = header(2, seq_number, length)
	return MTP_header

def header(type, seq_number, length):
	packet_header[0].type = type
	packet_header[0].seqNum = seq_number
	packet_header[0].length = length
	type_header = type.to_bytes(4,'big')
	seq_header = seq_number.to_bytes(4,'big')
	length_header = length.to_bytes(4,'big')
	MTP_header = type_header + seq_header + length_header
	check_sum = zlib.crc32(MTP_header)
	check_header = check_sum.to_bytes(4,'big')
	packet_header[0].checksum = check_header.hex()
	MTP_header += check_header
	return MTP_header



def extract_packet_info(packet_from_sender):
    # read packet
    state = "CORRUPT"
    type = int(packet_from_sender[0:4].hex(), 16)
    seqNum = int(packet_from_sender[4:8].hex(), 16)
    length = int(packet_from_sender[8:12].hex(), 16)
    checksum = packet_from_sender[12:16].hex()
    new_checksum = zlib.crc32(packet_from_sender[0:12]).to_bytes(4,'big')[0:4].hex()
    if(checksum == new_checksum):
        state = "NOT_CORRUPT"
    if(type == 1):
        t = "DATA"
    else:
        t = "ACK"
    return t, seqNum, length, checksum, new_checksum, state

def send_thread(sock):
    global recv_addr
    while True:
        # send ack packets but using unreliable channel
        if(ack_queue):
             with lock:
                seq_number = ack_queue.popleft()
                packet_header.append(PacketHeader)
                packet = create_packet(seq_number, 16)
                unreliable_channel.send_packet(sock, packet, recv_addr)
                with open(log_file, "a") as log:
                    str = "Packet sent; type=ACK; seqNum=%d; length=%d; checksum=%s\n\n" % (packet_header[0].seqNum, packet_header[0].length, packet_header[0].checksum)
                    log.write(str)
                    packet_header.pop(0)
             


def receive_thread(sock):
    global recv_addr
    global expect_number
    with open(output_file, 'wb') as f, open(log_file, 'a') as log:
        while True:
            packet_from_sender, recv_addr = unreliable_channel.recv_packet(sock)
            t, seqNum, length, checksum, new_checksum, state = extract_packet_info(packet_from_sender)
            str = "Packet received; type=%s; seqNum=%d; length=%d; checksum_in_packet=%s;\n" % (t, seqNum, length, checksum)
            log.write(str)
            str = "checksum_calculated=%s; status=%s\n\n" % (new_checksum, state)
            log.write(str)
            if(seqNum == expect_number):
                 f.write(packet_from_sender[16:])
                 expect_number += 1
            with lock:
                ack_queue.append(expect_number - 1)


def main():
    # Some of the things to do:
    # open log file and start logging
	# read the command line arguments
	# open UDP socket
    if(len(sys.argv) != 4):
        sys.exit("Not correct command argument.")
    receive_port = int(sys.argv[1])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", receive_port))
    # start send thread that sends back the acks (modify as needed)
    recv_thread = threading.Thread(target=receive_thread,args=(sock,))
    s_thread = threading.Thread(target=send_thread,args=(sock,))
    recv_thread.start()
    s_thread.start()
    
    recv_thread.join()
    s_thread.join()
    
    
    sock.close()
    log_file.close()
    output_file.close()
    
if __name__ == "__main__":
    main()

