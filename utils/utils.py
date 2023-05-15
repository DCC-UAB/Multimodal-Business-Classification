import wandb
import torch
import torch.nn 
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
import pandas as pd
import os
import numpy as np 
from PIL import Image
from models.models import *
import gensim.downloader as api

def get_data(slice=1, train=True):
    full_dataset = torchvision.datasets.MNIST(root=".",
                                              train=train, 
                                              transform=transforms.ToTensor(),
                                              download=True)
    #  equiv to slicing with [::slice] 
    sub_dataset = torch.utils.data.Subset(
      full_dataset, indices=range(0, len(full_dataset), slice))
    
    return sub_dataset


def make_loader(dataset, batch_size):
    loader = DataLoader(dataset=dataset,
                        batch_size=batch_size, 
                        shuffle=True,
                        pin_memory=True, num_workers=2)
    return loader


def make(config, device="cuda"):
    # Make the data
    train, test = get_data(train=True), get_data(train=False)
    train_loader = make_loader(train, batch_size=config.batch_size)
    test_loader = make_loader(test, batch_size=config.batch_size)

    # Make the model
    model = ConvNet(config.kernels, config.classes).to(device)

    # Make the loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        model.parameters(), lr=config.learning_rate)
    
    return model, train_loader, test_loader, criterion, optimizer

# It loads the labels of the images and split them into train, test and validation
def load_labels_and_split(path_sets, random_state=42):
    list_sets = os.listdir(path_sets)
    images_class = {}

    # Load the labels of the images and split them into train, test and validation
    for set_filename in list_sets:
        if "_" in set_filename:
            with open(path_sets + "/" + set_filename, "r") as file:
                file_text = file.read().splitlines()
            images_class[set_filename] = [row.split()[0] for row in file_text if row.split()[1] == "1"]
    
    train_img_names = []
    y_train = []
    test_img_names = []
    y_test = []
    for key in images_class.keys():
        if "train" in key:
            for image in images_class[key]:
                train_img_names.append(image + ".jpg")
                y_train.append(key.split("_")[0])
        elif "test" in key:
            for image in images_class[key]:
                test_img_names.append(image + ".jpg")
                y_test.append(key.split("_")[0]) 

    test_img_names, val_img_names, y_test, y_val = train_test_split(test_img_names, y_test, test_size=0.4, stratify=y_test, random_state=random_state)
    return train_img_names, y_train, test_img_names, y_test, val_img_names, y_val


# Loads the images and creates a dataframe with the correpondent labels
def load_images(img_names, labels, data_dir):
    img_dir = data_dir + "JPEGImages"

    list_img = []
    for img_name in img_names:
        img = Image.open(os.path.join(img_dir, img_name)) 
        list_img.append(np.array(img))

    data = pd.DataFrame()
    data["img"] = list_img
    data["label"] = labels
    data["name"] = img_names
    data.set_index("name", inplace=True)
    data["label"] = data["label"].astype(int)

    return data


# Adds the columns of two dataframes
def merge_data(imagesAndLabels, ocr_data):
    data = pd.concat([imagesAndLabels, ocr_data], axis=1, join="inner")
    return data


# Call this function to get the dataframes of the data, if train is True, it will return the train and validation dataframes,
#  if not, it will return the test dataframe
def make_dataframe(data_dir, anotation_path, train=True):
    sets_dir = data_dir + "/ImageSets/0"
    train_img_names, y_train, test_img_names, y_test, val_img_names, y_val = load_labels_and_split(sets_dir)
    ocr_data = pd.read_pickle(anotation_path)
    if train:
        train_data = load_images(train_img_names, y_train, data_dir)
        val_data = load_images(val_img_names, y_val, data_dir)
        train_data = merge_data(train_data, ocr_data)
        val_data = merge_data(val_data, ocr_data)
        return train_data, val_data
    else:
        test_data = load_images(test_img_names, y_test, data_dir)
        test_data = merge_data(test_data, ocr_data)
        return test_data
    
class Dataset_ConText(Dataset):
    def __init__(self, data, transform=None):
        self.data = data
        self.transform = transform
        self.w2v = api.load('glove-wiki-gigaword-300')
        self.dim_w2v = 300
        self.vocab = set(self.w2v.key_to_index.keys())
        self.max_n_words = 20

    def __len__(self):
        return len(self.data.index)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

        img = self.data.iloc[idx, 0]
        label = self.data.iloc[idx, 1]
        words_OCR = self.data.iloc[idx, 2]

        if self.transform:
            img = self.transform(img)

        words = np.zeros((self.max_n_words, self.dim_w2v))
        i = 0
        for word in list(set(words_OCR)):
            if len(word) > 2:
                if word.lower() in self.vocab:
                    words[i,:] = self.w2v[word.lower()]
                    i += 1
        return (label-1), img, np.array(words)