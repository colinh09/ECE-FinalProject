# Written by S. Mevawala, modified by D. Gitzel
# Edited by Colin Hwang, Faith Lin, and Yuri Hu

import logging

import channelsimulator
import utils
import sys
import socket

class Sender(object):

    def __init__(self, inbound_port=50006, outbound_port=50005, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.sndr_setup(timeout)
        self.simulator.rcvr_setup(timeout)

    def send(self, data):
        raise NotImplementedError("The base API class has no implementation. Please override and add your own.")


class BogoSender(Sender):

    def __init__(self):
        super(BogoSender, self).__init__()


    def send(self, data):
        self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))
        while True:
            try:
                self.simulator.u_send(data)  # send data
                ack = self.simulator.u_receive()  # receive ACK
                self.logger.info("Got ACK from socket: {}".format(
                    ack.decode('ascii')))  # note that ASCII will only decode bytes in the range 0-127
                break
            except socket.timeout:
                pass


class RDTsender(BogoSender):
    def __init__(self, timeout = 0.1):
        super(RDTsender, self).__init__()
        self.simulator.rcvr_setup(timeout)
        self.simulator.sndr_setup(timeout)

    # following rdt 3.0 protocol
    # override the send method
    def send(self, data):
        self.logger.info("Sending on port: {} and waiting for ACK on port: {}".format(self.outbound_port, self.inbound_port))
        num_ack = 1
        n = 1000
        data_seg = [data[i * n:(i + 1) * n] for i in range((len(data) + n - 1) // n)]
        timeout = 0
        resend = False
        for seg in data_seg:
            self.logger.info("Attempting to send next data packet.")
            while True:
                try:
                    if not resend:
                        #checksum to check if packet is corrupted
                        checksum = sum(seg)
                        length = 9
                        data_checksum = ('%%0%dx' % (length << 1) %checksum).decode('hex')[-length:]
                        seg.extend((data_checksum))
                        seg.extend(bytes(bytearray([num_ack])))
                    self.simulator.u_send(seg)  # send data
                    self.logger.info("Data packet has been sent.")
                    #ack has been been sent from the reciever
                    ack = self.simulator.u_receive()  
                    if ack == bytes(num_ack):
                        self.logger.info("Retrieved socket from receiver.")
                        num_ack += 1
                        # clear number of acks and timeout
                        if num_ack > 255:
                            num_ack = 1
                        timeout = 0
                        resend= False
                        break
                    # acks do not match. Must resent data packet
                    self.logger.info("Retrieved the wrong ACK.")
                    resend = True
                # resend packet if there is a timeout
                except socket.timeout:
                    timeout += 1
                    if timeout == 3:
                        sys.exit()
                    continue
        self.simulator.u_send(bytes("sent"))
        sys.exit()

if __name__ == "__main__":
    DATA = bytearray(sys.stdin.read())
    # sndr = BogoSender()
    sndr = RDTsender()
    sndr.send(DATA)