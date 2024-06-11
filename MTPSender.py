## The code provided here is just a skeleton that can help you get started
## You can add/remove functions as you wish


## import (add more as you need)
import threading
import unreliable_channel
import zlib
import sys
import os
import socket


## define and initialize
window_size = 0
window_base = 0
next_seq_number = 0
ack_counts = {}
packet_timers = {}
packet_header = []
packet_status = []

lock = threading.Lock()

class PacketStatus:
	def __init__(self, sent=False, needs_retransmission=False, ack = False):
		self.sent = sent
		self.needs_retransmission = needs_retransmission
		self.ack = ack

class PacketHeader:
	def __init__(self, type = 1, seqNum = 0, length = 0, checksum = 0):
		self.type = type
		self.seqNum = seqNum
		self.length = length
		self.checksum = checksum




def create_packet(seq_number, data, length):
# create data packet
# crc32 available through zlib library
	MTP_header = header(1, seq_number, length)
	data_packet = MTP_header + data
	return data_packet

def header(type, seq_number, length):
	packet_header[seq_number].type = type
	packet_header[seq_number].seqNum = seq_number
	packet_header[seq_number].length = length
	type_header = type.to_bytes(4,'big')
	seq_header = seq_number.to_bytes(4,'big')
	length_header = length.to_bytes(4,'big')
	MTP_header = type_header + seq_header + length_header
	check_sum = zlib.crc32(MTP_header)
	check_header = check_sum.to_bytes(4,'big')
	packet_header[seq_number].checksum = check_header.hex()
	MTP_header += check_header
	return MTP_header

def packet_timeout(seq_number):
	with lock:
		packet_status[seq_number].needs_retransmission = True

def start_timer(seq_number):
    timer = threading.Timer(0.5, packet_timeout, [seq_number])
    packet_timers[seq_number] = timer
    timer.start()

def stop_timer(seq_number):
    if seq_number in packet_timers:
        packet_timers[seq_number].cancel()


def send_thread(sock,packets,recv_addr, log_file):
	global window_base
	global next_seq_number
	while next_seq_number < len(packets) or any(pkt.needs_retransmission for pkt in packet_status):
		with lock:
			while next_seq_number < window_base + window_size and next_seq_number < len(packets):
				for seq_num, status in enumerate(packet_status):
					# If there is Triple duplicate ACKs or Time out, push window base and seq number back to the oldest unack pack
					if(status.needs_retransmission == True and seq_num <= next_seq_number):
						unreliable_channel.send_packet(sock,packets[seq_num],recv_addr)
						str = "Packet sent; type=DATA; seqNum=%d; length=%d; checksum=%s\n\n" % (seq_num, packet_header[seq_num].length, int(packet_header[seq_num].checksum))
						log_file.write(str)
						start_timer(seq_num)
						status.sent = True
						status.needs_retransmission = False
						status.ack = False
						next_seq_number = seq_num + 1
						window_base = seq_num
						break
				# Send packet
				unreliable_channel.send_packet(sock, packets[next_seq_number], recv_addr)
				str = "Packet sent; type=DATA; seqNum=%d; length=%d; checksum=%s\n\n" % (next_seq_number, packet_header[next_seq_number].length, packet_header[next_seq_number].checksum)
				log_file.write(str)
				start_timer(next_seq_number)
				packet_status[next_seq_number].sent = True
				packet_status[next_seq_number].needs_retransmission = False
				packet_status[next_seq_number].ack = False
				next_seq_number += 1
			


def extract_packet_info(packet_from_receiver):
# extract the ack after receiving
	state = "CORRUPT"
	type = int(packet_from_receiver[0:4].hex(), 16)
	seqNum = int(packet_from_receiver[4:8].hex(), 16)
	length = int(packet_from_receiver[8:12].hex(), 16)
	checksum = packet_from_receiver[12:16].hex()
	new_checksum = zlib.crc32(packet_from_receiver[0:12]).to_bytes(4,'big')[0:4].hex()
	if(checksum == new_checksum):
		state = "NOT_CORRUPT"
	if(len(packet_from_receiver) != 16):
		state = "CORRUPT"
	if(type == 1):
		t = "DATA"
	else:
		t = "ACK"
	return t, seqNum, length, checksum, new_checksum, state
	


def receive_thread(sock, log_file):
	global ack_counts
	global packet_status
	global window_base
	while True:
		# receive ack, but using our unreliable channel
		# packet_from_receiver, receiver_addr = unreliable_channel.recv_packet(socket)
		# call extract_packet_info
		# check for corruption, take steps accordingly
		# update window size, timer, triple dup acks
			packet_from_receiver, _ = unreliable_channel.recv_packet(sock)
			t, seqNum, length, checksum, new_checksum, state = extract_packet_info(packet_from_receiver)
			stop_timer(seqNum)
			str = "Packet received; type=%s; seqNum=%d; length=%d; checksum_in_packet=%s;\n" % (t, seqNum, length, checksum)
			log_file.write(str)
			str = "checksum_calculated=%s; status=%s\n\n" % (new_checksum, state)
			log_file.write(str)
			with lock:
				ack_counts[seqNum] = ack_counts.get(seqNum, 0) + 1
				# handle Triple duplicate ACKs
				if(ack_counts[seqNum] == 3):
					str = "Triple dup acks received for packet seqNum=%d\n\n" % (seqNum)
					log_file.write(str)
					packet_status[seqNum].needs_retransmission = True
				# push window_base forward
				if(seqNum >= window_base):
					window_base = seqNum + 1
					packet_status[seqNum].ack = True
				


def main():
	global window_size
	# some of the things to do:
    # open log file and start logging
    # read the command line arguments
	# open UDP socket
	if(len(sys.argv) != 6):
		sys.exit("Not correct command argument.")
	# read command line argument
	receive_ip = sys.argv[1]
	receive_port = int(sys.argv[2])
	window_size = int(sys.argv[3])
	input_file = sys.argv[4]
	log_file = open(sys.argv[5], "w")

	file = open(input_file)
	file.seek(0, os.SEEK_END)
	file_size = file.tell()
	file.close()

	# divide input file to packet
	num_packet = (file_size // 1456)
	packets = []
	seq_number = 0
	# take the input file and split it into packets (use create_packet)
	with open(input_file, "rb") as f:
		while(seq_number <= num_packet):
			packet_status.append(PacketStatus())
			packet_header.append(PacketHeader())
			#if(seq_number == num_packet):
			#	data_packet = create_packet(seq_number, f.read(remain_input), remain_input + 16)
			#else:
			data_packet = create_packet(seq_number, f.read(1456), 1472)
			seq_number += 1
			packets.append(data_packet)
	f.close()



	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	recv_addr = (receive_ip, receive_port)
	# start receive thread (modify as needed) which receives ACKs
	recv_thread = threading.Thread(target=receive_thread,args=(sock, log_file))
	s_thread = threading.Thread(target=send_thread, args=(sock,packets,recv_addr, log_file))
	s_thread.start()
	recv_thread.start()
	s_thread.join()
	recv_thread.join()
	sock.close()
	log_file.close()


if __name__ == "__main__":
    main()