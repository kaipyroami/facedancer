# USBProxy.py

# Contains class definitions to implement a simple USB Serial chip,
# such as the one in the HP48G+ and HP50G graphing calculators.  See
# usb-serial.txt in the Linux documentation for more info.

import facedancer

from facedancer.USB import *
from facedancer.USBDevice import *
from facedancer.USBConfiguration import *
from facedancer.USBInterface import *
from facedancer.USBEndpoint import *
from facedancer.USBVendor import *
from facedancer.errors import *

import usb
from usb.core import USBError


class USBProxyFilter:

    def filter_control_in(self, req, data):
        return req, data

    def filter_control_out(self, req, data):
        return req, data

    def filter_in(self, data):
        return data

    def filter_out(self, data):
        return data


class USBProxyDevice(USBDevice):
    name = "Base class for proxied USB devices"

    filter_list = []

    def __init__(self, maxusb_app, idVendor, idProduct, verbose=0):

        # Open a connection to the proxied device...
        self.libusb_device = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        if self.libusb_device is None:
            raise DeviceNotFoundError("Could not find device to proxy!")

        # TODO: Do this thing
        # self.libusb_device.detach_kernel_driver(0)

        # ... and initialize our base class with a minimal set of parameters.
        # We'll do almost nothing, as we'll be proxying packets by default to the device.
        USBDevice.__init__(self,maxusb_app,verbose=verbose)


    def add_filter(self, filter_object, head=False):
        if head:
            self.filter_list.insert(0, filter_object)
        else:
            self.filter_list.append(filter_object)

    def handle_request(self, req):
        if self.verbose > 3:
            print(self.name, "received request", req)

        try:
            self._proxy_request(req)
        except USBError as e:
            print("STALLING")
            print(e)
            self.maxusb_app.stall_ep0()


    def _proxy_request(self, req):
        """
        Proxies EP0 requests between the victim and the target. 
        """
        if req.get_direction() == 1:
            self._proxy_in_request(req)
        else:
            self._proxy_out_request(req)


    def _proxy_in_request(self, req):
        """
        Proxy IN requests, which gather data from the target device and
        forward it to the victim.
        """

        # Read any data from the real device...
        data = self.libusb_device.ctrl_transfer(req.request_type, req.request,
                                     req.value, req.index, req.length)

        # Run filters here.
        for f in self.filter_list:
            req, data = f.filter_control_in(req, data)
        print("<", data)

        #... and proxy it to our victim.
        self.send_control_message(data)


    def _proxy_out_request(self, req):
        """
        Proxy OUT requests, which sends a request from the victim to the
        target device.
        """
       
        # If the victim is trying to send data with the request, read it...
        if req.length:
            data = self.maxusb_app.read_from_endpoint(0)
        else:
            data = []

        # Run filters here.
        print("OUT ", req)
        for f in self.filter_list:
            req, data = f.filter_control_out(req, data)
        if data:
            print(">", data)

        # ... forward the request to the real device.
        if req:
            self.libusb_device.ctrl_transfer(req.request_type, req.request,
                req.value, req.index, data)
            self.ack_status_stage()


    def handle_data_available(self, ep_num, data):
        print("FAIL! data available and we didn't do anything about it")
    

    def handle_buffer_available(self, ep_num):
        print("FAIL! buffer available and we didn't do anything about it")
