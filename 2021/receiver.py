# Written by S. Mevawala, modified by D. Gitzel
# Edited by Colin Hwang, Faith Lin, and Yuri Hu

import logging

import channelsimulator
import utils
import sys
import socket

class Receiver(object):

    def __init__(self, inbound_port=50005, outbound_port=50006, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.rcvr_setup(timeout)
        self.simulator.sndr_setup(timeout)

    def receive(self):
        raise NotImplementedError("The base API class has no implementation. Please override and add your own.")


class BogoReceiver(Receiver):
    ACK_DATA = bytes(123)

    def __init__(self):
        super(BogoReceiver, self).__init__()

    def receive(self):
        self.logger.info("Receiving on port: {} and replying with ACK on port: {}".format(self.inbound_port, self.outbound_port))
        while True:
            try:
                 data = self.simulator.u_receive()  # receive data
                 self.logger.info("Got data from socket: {}".format(
                     data.decode('ascii')))  # note that ASCII will only decode bytes in the range 0-127
                 sys.stdout.write(data)
                 self.simulator.u_send(BogoReceiver.ACK_DATA)  # send ACK
            except socket.timeout:
                sys.exit()


class RDTreceiver(BogoReceiver):
    def __init__(self, timeout = 0.1):
         super(RDTreceiver, self).__init__()
         self.timeout = timeout
         self.simulator.rcvr_setup(timeout)
         self.simulator.sndr_setup(timeout)
    # override the receive method
    def receive(self):
        self.logger.info("Receiving on port: {} and replying with ACK on port: {}".format(self.inbound_port, self.outbound_port))
        ACK = 1
        timeout = 0
        valid_length = 10
        checksum_length = 9
        while True:
            try:
                 packet_received = False
                 ACK_DATA = bytes(ACK)
                 # get data from the sender
                 data = self.simulator.u_receive()
                 if data == bytes("sent"):
                    break
                 data_packet = data[:len(data)-valid_length]
                 validation_data = data[len(data)-valid_length:]
                 valid_ack = validation_data[-1]
                 valid_checksum = validation_data[:-1]
                 # checksum to prevent data from being corrupted
                 checksum = sum(data_packet)
                 checksum = ('%%0%dx' % (checksum_length << 1) % checksum).decode('hex')[-checksum_length:]
                 # if data is corrupted
                 if checksum == valid_checksum and ACK > valid_ack:
                    self.simulator.u_send(bytes(valid_ack))
                    self.logger.info("Wrong ACK was sent.")
                    timeout = 0
                 # recieved data properly, can move on
                 elif checksum == valid_checksum and ACK == valid_ack:
                    if not packet_received:
                        self.logger.info("Data has been sent from sender.")
                        self.logger.info("Sending ACK back to sender.")
                        # deal with duplicate packets
                        sys.stdout.write(data_packet)
                        packet_received = True
                    # send ack to the sender
                    self.simulator.u_send(bytes(ACK))
                    self.logger.info("Data has been properly received.")
                    ACK += 1
                    if ACK > 255:
                        ACK = 1
                    timeout = 0
                 else:
                    self.logger.info("Recieved the wrong packet.")
                    self.simulator.u_send(bytes("diff"))
            except socket.timeout:
                self.simulator.u_send(bytes("Timeout"))
                timeout += 1
                if timeout == 2:
                    sys.exit()
            # error with decoding, resend packet
            except UnicodeDecodeError:
                self.logger.info("Unicode error")
                self.simulator.u_send(bytes("Unicode"))
                continue
            except:
                pass

if __name__ == "__main__":
    # rcvr = BogoReceiver()
    rcvr = RDTreceiver()
    rcvr.receive()