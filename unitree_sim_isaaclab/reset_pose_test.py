#!/usr/bin/env python3
"""
publish reset category command to rt/reset_pose/cmd
"""

import time
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_

def publish_reset_category(category: int,publisher):
    # construct message
    msg = String_(data=str(category))  # pass data parameter directly during initialization

    # create publisher

    # publish message
    publisher.Write(msg)
    print(f"published reset category: {category}")

if __name__ == "__main__":
    # initialize DDS
    ChannelFactoryInitialize(1)
    publisher = ChannelPublisher("rt/reset_pose/cmd", String_)
    publisher.Init()

    for cat in [1]:
        publish_reset_category(cat,publisher)
        time.sleep(1)  # wait for 1 second
    print("test publish completed")