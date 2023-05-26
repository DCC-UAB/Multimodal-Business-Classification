import os
import random
import wandb

import numpy as np
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms

from train import *
from test import *
from utils.utils import *
from tqdm.auto import tqdm

# Ensure deterministic behavior
torch.backends.cudnn.deterministic = True
random.seed(hash("setting random seeds") % 2**32 - 1)
np.random.seed(hash("improves reproducibility") % 2**32 - 1)
torch.manual_seed(hash("by removing stochasticity") % 2**32 - 1)
torch.cuda.manual_seed_all(hash("so runs are repeatable") % 2**32 - 1)

# Device configuration
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def model_pipeline(cfg:dict) -> None:
    # tell wandb to get started
    with wandb.init(project="business_recognition", config=cfg):
      # access all HPs through wandb.config, so logging matches execution!
      config = wandb.config

      # make the model, data, and optimization problem
      model, criterion, optimizer, train_loader, test_loader, val_loader = make(config)
      # and use them to train the model
      train(model, train_loader, val_loader, criterion, optimizer, config)
      
      # and test its final performance
      test(model, test_loader, config=config, save=True)

    return model

if __name__ == "__main__":
    wandb.login()

    config = dict(
        epochs=35,
        classes=28,
        batch_size=13,
        batch_size_val_test=13,
        learning_rate=0.00006,
        patience=10,
        heads=8,
        depth=4,
        fc_transformer=340,
        dropout=0.4,
        dataset="ConText",
        architecture="Transformer",
        cnn = "MobileNetV3",
        weights = "DEFAULT",
        name_model="glove_transformer_depth_4_head_n_8_drop_0_4_mobilnet.pkl")
    model = model_pipeline(config)

