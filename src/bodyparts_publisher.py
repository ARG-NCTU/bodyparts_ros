#!/usr/bin/env python3

# -- IMPORT --
import numpy as np
import cv2
import torch
# Ros
import rospy
import cv_bridge
from sensor_msgs.msg import CompressedImage
# Ros bodyparts
from helper_refinenet.resnet import rf_lw50, rf_lw101, rf_lw152
from helper_refinenet.helpers import prepare_img


class Bodyparts:
    def __init__(self):
        # Parameter
        self.cam_rgb = rospy.get_param('/bodyparts/camera/rgb')
        self.interface = rospy.get_param('/bodyparts/interface/topic')
        self.model_type = rospy.get_param('/bodyparts/model')

        # Init
        self.bridge = cv_bridge.CvBridge()
        if(self.model_type == 50):
            self.model = rf_lw50(7, pretrained=True).eval().cuda()
        elif(self.model_type == 101):
            self.model = rf_lw101(7, pretrained=True).eval().cuda()
        elif(self.model_type == 152):
            self.model = rf_lw152(7, pretrained=True).eval().cuda()
        else:
            raise KeyError('Wrong model type -> correct config file')

        # Publisher
        self.pub_mask = rospy.Publisher(self.interface, CompressedImage, queue_size=1)

        # Subscriber
        rospy.Subscriber(self.cam_rgb, CompressedImage, self._callback, queue_size=1)

        # Feedback
        print("Body segmentation publisher up and running")


    # Callback function
    def _callback(self, msg):

        t_start = rospy.get_time()

        image = cv2.cvtColor(self.bridge.compressed_imgmsg_to_cv2(msg), cv2.COLOR_BGR2RGB)
        
        with torch.no_grad():
            image_tensor = torch.tensor(prepare_img(image).transpose(2,0,1)[None]).float()
            
            image_input = image_tensor.cuda()

            mask = self.model(image_input)[0].data.cpu().numpy().transpose(1,2,0)
            mask = cv2.resize(mask, image.shape[:2][::-1], interpolation=cv2.INTER_CUBIC)
            mask = mask.argmax(axis=2).astype(np.uint8)
        
        print('Body detection successful. Current Hz-rate:\t' + str(1/(rospy.get_time() - t_start)))
        self.pub_mask.publish(self.bridge.cv2_to_compressed_imgmsg(mask))


if __name__ == '__main__':

    rospy.init_node('bodyparts_publisher')
    body = Bodyparts()
    rospy.spin()