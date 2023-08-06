import datetime

import torch
import torch.nn as nn
import numpy as np
from PIL import Image
import torchvision
from torchvision import transforms


class Preproc(nn.Module):

    def __init__(self, agent_params):
        super(Preproc, self).__init__()

        self.agent_params = agent_params
        self.height = self.agent_params['downsample_w']
        self.width = self.agent_params['downsample_h']

    def forward(self, x: torch.Tensor):
        if x.dim() > 3:
            x = x[0]

        x = x.float()

        if self.agent_params["use_rgb_for_raw_state"]:
            x = np.dot(x[..., :3], [0.299, 0.587, 0.114])
            x = torch.from_numpy(x)
            x = x.float()

        x = x.reshape(1, 240, 256)

        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((self.width, self.height), interpolation=Image.BILINEAR),
            transforms.ToTensor()
        ])

        x = transform(x)

        x = x[0]

        # Disable this code for now
        # now = datetime.datetime.now()
        # newImage = Image.new('RGB', (self.width, self.height))
        # for i in range(0,self.width):
        #     for j in range (0,self.height):
        #         value = x[i,j]
        #         value = int(value.item() * 255)
        #         newImage.putpixel((j,i),(value,value,value))
        # newImage.save("../../image_snapshot/snapshot" + str(now.strftime("%H-%M-%S")) + ".png", 'PNG')

        return x
