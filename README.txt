MTP specifications
Types of packets and packet size
MTP specifies only two types of packets: DATA and ACK. The sender sends the DATA packets and 
when the receiver receives them, ACK packets are sent back. Since MTP is a reliable delivery protocol, 
the DATA packets and ACKs should contain a sequence number. The data packet has a header with the following fields

1. type (unsigned integer): data or ack
2. seqNum (unsigned integer): sequence number
3. length (unsigned integer): length of data including the MTP header fields
4. checksum (unsigned integer): 4 bytes CRC

MTP reliable delivery policy
MTP relies on the following rules to ensure reliable delivery:
Sequence number: Each packet from the sender to the receiver should include a sequence
number. The sender reads the input file, splits it into appropriate-sized chunks of data, puts it
into an MTP data packet, and assigns a sequence number to it.
- The sender will use 0 as the initial sequence number.
- Unlike TCP, we will use sequence numbers of each packet and not for the byte stream.

Checksum: The integrity of the packet (meaning if it is corrupt or not) is validated using a
checksum. After determining the values of the first three fields of the MTP header (type,
seqNum, and length) and the data that goes in the packet, the sender calculates a 32-bit
checksum of these three fields and data and puts it in the checksum field in the MTP header.

Sliding window: The sender uses a sliding window mechanism. The size of the window will be 
specified in the command line. The window only depends on the number of unacknowledged packets 
and does not depend on the receiver’s available buffer size (i.e., MTP does not have any flow control). 
Proper implementation of the sender window is required.

Timeout: The sender will use a fixed value of 500ms as the timeout. Similar to TCP, the timer is
running for the oldest unacked packet.
The receiver uses the following rules while ACKing the sender
- The receiver acknowledges every packet, it does not use cumulative acks or delayed acks.
- The receiver acks the last correctly received in-order packet (not the one it expects next
as in TCP).

$> ./MTPSender <receiver-IP> <receiver-port> <window-size> <input-file> <sender-log-file>

$> ./MTPReceiver <receiver-port> <output-file> <receiver-log-file>
