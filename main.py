from __future__ import print_function, division

from alexnet  import *
import torch
import torch.nn as nn
import torch.nn.functional as f
from torch.autograd import Variable
import numpy as np
import torch.optim as optim
import torchvision
from torchvision import datasets, models, transforms
import pickle, os, glob
import torch.backends.cudnn as cudnn
from PIL import Image
import matplotlib.pyplot as plt
from datetime import datetime
import copy
import os
import sys, getopt
from Utils import *
use_gpu = 0
gpus=[0,1,2]
plt.ion()   # interactive mode
os.environ['CUDA_VISIBLE_DEVICES'] = '0' #selecting the graphic processor
cudnn.benchmark = True #-- uses the inbuilt cudnn auto-tuner to find the fastest convolution algorithms.
                       #-- If this is set to false, uses some in-built heuristics that might not always be fastest.

cudnn.fastest = True #-- this is like the :fastest() mode for the Convolution modules,
                     #-- simply picks the fastest convolution algorithm, rather than tuning for workspace size
imSize = 225
batchSize = 32
nb_epoch = 50


data_dir	 = "./dataset/"

data_transforms = {
    'train': transforms.Compose([
        transforms.RandomSizedCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
    'val': transforms.Compose([
        transforms.Scale(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ]),
}

dsets = {x: datasets.ImageFolder(os.path.join(data_dir, x), data_transforms[x])for x in ['train', 'val']}

dset_loaders = {x: torch.utils.data.DataLoader(dsets[x], batch_size=100, shuffle=True, num_workers=4) for x in ['train', 'val']}

dset_sizes = {x: len(dsets[x]) for x in ['train', 'val']}
dset_classes = dsets['train'].classes

def imshow(inp, title=None):
    """Imshow for Tensor."""
    inp = inp.numpy().transpose((1, 2, 0))
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    inp = std * inp + mean
    plt.imshow(inp)
    if title is not None:
        plt.title(title)
    plt.pause(5)  # pause a bit so that plots are updated

# Get a batch of training data
inputs, classes = next(iter(dset_loaders['train']))

# Make a grid from batch
out = torchvision.utils.make_grid(inputs)

#imshow(out, title=[dset_classes[x] for x in classes])
def exp_lr_scheduler(optimizer, epoch, init_lr=0.001, lr_decay_epoch=7):
    """Decay learning rate by a factor of 0.1 every lr_decay_epoch epochs."""
    lr = init_lr * (0.1**(epoch // lr_decay_epoch))

    if epoch % lr_decay_epoch == 0:
        print('LR is set to {}'.format(lr))

    for param_group in optimizer.param_groups:
        param_group['lr'] = lr

    return optimizer


def train_model(model, criterion, optimizer,  num_epochs=25):
    since = datetime.now()

    best_model = model
    best_acc = 0.0

    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)

        # Each epoch has a training and validation phase
        for phase in ['train', 'val']:
            if phase == 'train':
                model.train(True)  # Set model to training mode
            else:
                model.train(False)  # Set model to evaluate mode

            running_loss = 0.0
            running_corrects = 0

            # Iterate over data.
            for data in dset_loaders[phase]:
                # get the inputs
                inputs, labels = data

                # wrap them in Variable
                if use_gpu:
                    inputs, labels = Variable(inputs.cuda()), \
                        Variable(labels.cuda())
                else:
                    inputs, labels = Variable(inputs), Variable(labels)

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward
                outputs = model(inputs)[1]
                _, preds = torch.max(outputs.data, 1)
            	loss = criterion(outputs, labels)

                # backward + optimize only if in training phase
                if phase == 'train':
                    loss.backward()
                    optimizer.step()

                # statistics
                running_loss += loss.data[0]
                running_corrects += torch.sum(preds == labels.data)
		#if( preds != labels.data):
		#	print ( "predicted : {}, reality : {}".format(preds, labels.data)
                epoch_loss = running_loss / dset_sizes[phase]
                epoch_acc = running_corrects / dset_sizes[phase]

            print('{} Loss: {:.4f} Acc: {:.4f} Real_Loss : {:.4f}'.format(
                    phase, epoch_loss, epoch_acc, loss.data[0]))

            # deep copy the model
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model = copy.deepcopy(model)

        print()
    time_elapsed = datetime.now() - since
    print('Training complete in {:.0f}ms '.format(
        time_elapsed.microseconds /1000))
    print('Best val Acc: {:4f}'.format(best_acc))
    return best_model

#Function for displaying prediction for images
def visualize_model(model, num_images=3):
    images_so_far = 0
    fig = plt.figure()
    for i, data in enumerate(dset_loaders['val']):
        inputs, labels = data
        if use_gpu:
            inputs, labels = Variable(inputs.cuda()), Variable(labels.cuda())
        else:
            inputs, labels = Variable(inputs), Variable(labels)
        outputs = model(inputs)[1]
        _, preds = torch.max(outputs, 1)
        for j in range(inputs.size()[0]):
            images_so_far += 1
            ax = plt.subplot(num_images//2, 2, images_so_far)
            ax.axis('off')
            ax.set_title('predicted: {}'.format(dset_classes[labels.data[j]]))
            imshow(inputs.cpu().data[j])
            if images_so_far == num_images:
                return

def test_model(model):
    print ("testing our model with our evaluation data")
    model.train(False)
    corrects = 0
    total = 0
    hist_erreur = [0,0,0,0,0]
    nb_erreurs =[ [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0] ]
    for i,data in enumerate(dset_loaders['val']):
        inputs, labels = data
        if use_gpu:
            inputs, labels = Variable(inputs.cuda(device=gpus[0])), Variable(labels.cuda(device=gpus[0]))
        else:
            inputs, labels = Variable(inputs), Variable(labels)
        outputs = model(inputs)[1]
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        corrects += torch.sum(predicted == labels.data)
	for i in range(0,predicted.size()[0]):
            if( not predicted[i][0]==labels.data[i]):
	       hist_erreur[labels.data[i]]= hist_erreur[labels.data[i]] + 1
	       nb_erreurs[labels.data[i]][predicted[i][0]] = nb_erreurs[labels.data[i]][predicted[i][0]] + 1
    print('Accuracy of the network on the test images: %d %%' % (
        100 * corrects / total))
    print (hist_erreur)
    print (nb_erreurs)

def main(argv):
   try:
      opts, args = getopt.getopt(argv,"hi:o:",["gpu="])
   except getopt.GetoptError:
      print ("correct syntax : main.py --gpu <0/1 use_gpu>")
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print ("main.py --gpu <0/1 use_gpu>")
         sys.exit(0)
      elif opt in ("--gpu"):
         global use_gpu
         use_gpu = int(arg)
   print ('Use gpu ? ', use_gpu)

def train_from_scratch():
    print ("gpu is : ", use_gpu)
    #we use a pretrained model of Alexnet and copy only features into our model
    alexnextmodel = alexnet(True)
    alexTunedClassifier = AlexNet()
    alexTunedClassifier.fc = nn.Linear(4096, 5)
    copyFeaturesParametersAlexnet(alexTunedClassifier, alexnextmodel)

    if use_gpu:
     	alexTunedClassifier.cuda()

    #test_model(alexTunedClassifier)

    criterion = nn.CrossEntropyLoss()
    #we dont train last layers
    optimizer=optim.SGD([{'params': alexTunedClassifier.classifier.parameters()},
                         {'params': alexTunedClassifier.features.parameters(), 'lr': 0.0}
                        ], lr=0.001, momentum=0.5)

    model2 = train_model(alexTunedClassifier, criterion, optimizer, num_epochs=5)
    torch.save(model2, "./model/alexnet-epoch5-lr_0.001_notcomplete.ckpt")
   # visualize_model(model2,10)
    test_model(model2)
    model2 = torch.load( "./model/alexnet-epoch5-lr_0.001_notcomplete.ckpt")
   # visualize_model(model2,10)
    if(use_gpu):
    	model2.cuda()

    #we train everything but with a lower learning rate
    optimizer=optim.SGD(model2.parameters(), lr=0.001, momentum=0.9)

    model2 = train_model(model2, criterion, optimizer, num_epochs=5)
    torch.save(model2, "./model/alexnet-epoch5-lr_0.001_complete.ckpt")

    #we reduce again the learning rate
    optimizer=optim.SGD(model2.parameters(), lr=0.0001, momentum=0.9)
    model2 = train_model(model2, criterion, optimizer,num_epochs=5)
    torch.save(model2, "./model/alexnet-epoch5-lr_0.0001_complete.ckpt")
    #visualize_model(model2,3)
    #finally we test it completly and display results for this training
    test_model(model2)
    optimizer = optim.SGD(model2.parameters(), lr=0.00001, momentum=0.9)
    model2 = train_model(model2,criterion, optimizer,num_epochs=5)
    torch.save(model2, "./model/alexnet-epoch5-lr_0.00001_complete.ckpt")

    optimizer = optim.SGD(lr=0.00001, momentum=0.9)
    model2 = train_model(model2,criterion, optimizer,num_epochs=5)
    torch.save(model2, "./model/alexnet-epoch5-lr_0.00001_full.ckpt")

def test_network(network):
    model = torch.load(network)
    if( use_gpu):
        model.cuda()
    test_model(model)
def test_image(directory,network):
    image = random_file(directory)
    classes = ["poiting(1)","ok(2)","good(3)","fist(4)","palm(5)"]
    model = torch.load(network)
    since = datetime.now()
    if( use_gpu):
        model.cuda()
    model.eval()
    transform = transforms.Compose([
        transforms.Scale(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    imgPath = directory+image
    if (use_gpu):
        inp = Variable(transform(Image.open(imgPath)).unsqueeze(0).cuda(device=gpus[0]), volatile=True)
    else:
        inp = Variable(transform(Image.open(imgPath)).unsqueeze(0), volatile=True)
    logit = model(inp)[1]
    proba,pred = torch.max(logit.data,1)
    #print (proba[0][0])
    #print (pred[0][0])
    print ("result : {:.3f} for {}".format(proba[0][0],classes[pred[0][0]]))

    time_elapsed = datetime.now() - since
    print('Training complete in {}millisseconds'.format(time_elapsed.microseconds/1000 ))

if __name__ == '__main__':
    main(sys.argv[1:])
    #train_from_scratch()
    test_network("./model/alexnet-epoch5-lr_0.00001_complete.ckpt")
    #print ("test class 1 ")
    #test_image("./dataset/val/1/","./model/alexnet-epoch5-lr_0.0001_complete.ckpt")
    #print ("test class 2")
    #test_image("./dataset/val/2/","./model/alexnet-epoch5-lr_0.0001_complete.ckpt")
    #print("test class 3")
    #test_image("./dataset/val/3/","./model/alexnet-epoch5-lr_0.0001_complete.ckpt")
