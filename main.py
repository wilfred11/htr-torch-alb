import csv
import os
import random
import shutil
from collections import Counter
import pandas as pd

import numpy as np
import torch.nn as nn
import pickle
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader
from torchvision.transforms import v2
from torch import nn

import pywhatkit as pw

import torch.utils.data as data_utils
import albumentations as A
import torchinfo

from files.config import Config
from files.data import (
    read_words_generate_csv,
    read_bbox_csv_show_image,
    get_dataloaders,
    dataloader_show,
    read_maps,
    get_replay_dataset,
)
from files.dataset import (
    CustomObjectDetectionDataset,
    AHTRDataset,
    KFoldTransformedDatasetIterator,
    TransformedDatasetEpochIterator, AHTRDatasetOther,
)
from files.transform import ResizeWithPad, AResizeWithPad, train_transform
import torch
from files.model import (
    CRNN,
    visualize_model,
    visualize_featuremap,
    CRNN_lstm,
    CRNN_rnn,
    simple_model,
    CRNN_adv,
    advanced_model,
    simple_CNN,
    advanced_CNN,
    Attention,
)
from files.test_train import train, test
from files.functions import (
    generated_data_dir,
    htr_ds_dir,
    base_no_aug_score_dir,
    base_aug_score_dir,
    aug_graphs,
    no_aug_graphs,
    adv_no_aug_score_dir,
    adv_aug_score_dir,
)
from wakepy import keep

# Todo confusion matrix

device = "cuda" if torch.cuda.is_available() else "cpu"
image_transform = v2.Compose([ResizeWithPad(h=32, w=110), v2.Grayscale()])

do = 1
# aug = 0
# aug = 1

text_label_max_length = 8
model = 2
torch.manual_seed(1)
random_seed = 1
random.seed(random_seed)
np.random.seed(1)

# models = ["gru"]
models = ["gru"]
dropout = [0,.5]
augs = [0, 1]



if do == 110:
    print("saving images and transforms")
    read_words_generate_csv()
    config = Config("char_map_15.csv", 10)
    ds = get_replay_dataset(config)
    ds.save_pictures_and_transform1()
    ds.get_label_length_counts()

if do == 1:
    with keep.running() as k:
        t_folder = "test/"
        if os.path.isdir(t_folder):
            shutil.rmtree(t_folder)
        os.mkdir(t_folder)
        tfs = [
            "scores",
            "scores/adv",
            "scores/base",
            "scores/base/aug",
            "scores/adv/aug",
            "scores/base/no_aug",
            "scores/adv/no_aug",
            "scores/base/aug/drop",
            "scores/adv/aug/drop",
            "scores/base/no_aug/drop",
            "scores/adv/no_aug/drop",
        ]
        for tf in tfs:
            if os.path.isdir(tf):
                shutil.rmtree(tf)
            os.mkdir(tf)
        # augs = [0, 1]
        #augs = [0, 1]
        advs = [0]
        pretrain = 1
        stop_pretrain = 0

        read_words_generate_csv()

        config = Config("char_map_15.csv", 6)

        print("num classes: ", config.num_classes)
        print("blank_label: ", config.blank_label)
        print("empty_label: ", config.empty_label)
        print("char_set: ", config.char_set)
        print("int to char map: ", config.int_to_char_map)
        print("char to int map: ", config.char_to_int_map)

        dataset = AHTRDataset(
            "file_names-labels.csv",
            config,
            None,
            15040,
        )



        #dataset_ = torch.utils.data.ConcatDataset([dataset, dataset1])

        for model in models:
            for adv in advs:
                for aug in augs:
                    for drop in dropout:
                        if pretrain == 1:
                            dataset1 = AHTRDatasetOther(
                                "dirs.pkl",
                                config,
                                None,
                                5135,
                            )


                        test_image_transform = A.Compose([])
                        if aug == 1:
                            train_image_transform = train_transform()

                            #A.save(train_image_transform, "/scores/transform.json")
                        if aug == 0:
                            train_image_transform = A.Compose([])

                        with keep.running() as k:
                            print("htr training and testing")

                            if model == "gru" and adv == 0:
                                crnn = CRNN(config.num_classes, drop).to(device)
                            elif model == "lstm" and adv == 0:
                                crnn = CRNN_lstm(config.num_classes).to(device)
                            elif model == "rnn" and adv == 0:
                                crnn = CRNN_rnn(config.num_classes).to(device)
                            elif model == "gru" and adv == 1:
                                crnn = CRNN_adv(config.num_classes).to(device)

                            prefix = model + "_"

                            criterion = nn.CTCLoss(
                                blank=config.blank_label, reduction="mean", zero_infinity=True
                            )
                            # optimizer = torch.optim.Adam(crnn.parameters(), lr=0.001)
                            optimizer = torch.optim.Adam(
                                params=crnn.parameters(),
                                lr=0.001,
                                betas=(0.9, 0.999),
                                eps=1e-08,
                                weight_decay=0,
                                amsgrad=False,
                            )

                            if pretrain==1:
                                print("***************************")
                                print("pretraining")
                                for it in range(5):
                                    print("iteration "+str(it))
                                    for epoch in range(config.num_epoch):
                                        print("epoch "+ str(epoch))
                                        data_handler = TransformedDatasetEpochIterator(
                                            dataset1,
                                            current_epoch=epoch,
                                            num_epoch=config.num_epoch,
                                            train_transform=A.Compose([]),
                                            test_transform=A.Compose([]),
                                            seed=random_seed,
                                            train_val_split=[1,0]
                                        )
                                        train_data, test_data = data_handler.get_splits()

                                        trl = torch.utils.data.DataLoader(
                                            train_data, batch_size=4, shuffle=False
                                        )
                                        tl = torch.utils.data.DataLoader(
                                            test_data, batch_size=1, shuffle=False
                                        )
                                        train(
                                            [], trl, crnn, optimizer, criterion, config
                                        )

                                        test(tl, crnn, optimizer, criterion, config)

                                        if epoch == 4:
                                            break
                                print("end pretraining")
                                print("***************************")
                                #pretrain=0
                                #torch.save(crnn.state_dict(), prefix + "pretrained_reader")
                            print("xxxxxxxxxxxxxxxxxxxxxxxxxxxx")
                            print(
                                "context: " + model + " adv: " + str(adv) + " aug: " + str(aug) + " drop: " + str(drop))

                            # MAX_EPOCHS = 2500

                            # dataset
                            print("length ds: ", str(len(dataset)))
                            # dataloader_show(trl, number_of_images=2, int_to_char_map=int_to_char_map)

                            list_training_loss = []
                            list_testing_loss = []
                            list_testing_wer = []
                            list_testing_cer = []
                            list_length_correct = []
                            trained_on_words = []


                            for epoch in range(config.num_epoch):
                                print("epoch "+str(epoch))
                                data_handler = TransformedDatasetEpochIterator(
                                    dataset,
                                    current_epoch=epoch,
                                    num_epoch=config.num_epoch,
                                    train_transform=train_image_transform,
                                    test_transform=test_image_transform,
                                    seed=random_seed,
                                )
                                train_data, test_data = data_handler.get_splits()


                                trl = torch.utils.data.DataLoader(
                                    train_data, batch_size=4, shuffle=False
                                )
                                tl = torch.utils.data.DataLoader(
                                    test_data, batch_size=1, shuffle=False
                                )
                                training_loss, trained_on_words = train(
                                    trained_on_words, trl, crnn, optimizer, criterion, config
                                )
                                (
                                    testing_loss,
                                    wer,
                                    cer,
                                    length_correct,
                                    list_words,
                                    list_hypotheses,
                                ) = test(tl, crnn, optimizer, criterion, config)

                                list_training_loss.append(training_loss)
                                list_testing_loss.append(testing_loss)
                                list_testing_wer.append(wer)
                                list_testing_cer.append(cer)
                                list_length_correct.append(length_correct)

                                if drop!=0:
                                    if aug == 0 and adv == 0:
                                        dir = base_no_aug_score_dir()+"drop/"
                                    elif aug == 1 and adv == 0:
                                        dir = base_aug_score_dir()+"drop/"
                                    elif aug == 0 and adv == 1:
                                        dir = adv_no_aug_score_dir()+"drop/"
                                    elif aug == 1 and adv == 1:
                                        dir = adv_aug_score_dir()+"drop/"
                                else:
                                    if aug == 0 and adv == 0:
                                        dir = base_no_aug_score_dir()
                                    elif aug == 1 and adv == 0:
                                        dir = base_aug_score_dir()
                                    elif aug == 0 and adv == 1:
                                        dir = adv_no_aug_score_dir()
                                    elif aug == 1 and adv == 1:
                                        dir = adv_aug_score_dir()

                                columns = ["word", "hypothesis"]
                                with open(
                                    dir
                                    + prefix
                                    + "words_hypothesis_epoch_"
                                    + str(epoch)
                                    + ".csv",
                                    "w",
                                    newline="",
                                ) as f:
                                    write = csv.writer(f)
                                    write.writerow(columns)
                                    for i in range(len(list_words)):
                                        l = [list_words[i], list_hypotheses[i]]
                                        write.writerow(l)
                                print("xxxxxxxxxxxxxxxxxxxxxxxxxxxx")
                                if epoch == 4:
                                    print("training loss", list_training_loss)
                                    with open(
                                        dir + prefix + "list_training_loss.pkl", "wb"
                                    ) as f1:
                                        pickle.dump(list_training_loss, f1)
                                    print("testing loss", list_testing_loss)
                                    with open(
                                        dir + prefix + "list_testing_loss.pkl", "wb"
                                    ) as f2:
                                        pickle.dump(list_testing_loss, f2)
                                    with open(
                                        dir + prefix + "list_testing_wer.pkl", "wb"
                                    ) as f3:
                                        pickle.dump(list_testing_wer, f3)
                                    with open(
                                        dir + prefix + "list_testing_cer.pkl", "wb"
                                    ) as f4:
                                        pickle.dump(list_testing_cer, f4)
                                    with open(
                                        dir + prefix + "list_testing_length_correct.pkl",
                                        "wb",
                                    ) as f5:
                                        pickle.dump(list_length_correct, f5)

                                    trained_on_words_count = dict(Counter(trained_on_words))

                                    trained_on_words_count = dict(
                                        sorted(
                                            trained_on_words_count.items(),
                                            key=lambda item: len(item[0]),
                                        )
                                    )

                                    with open(
                                        dir + prefix + "trained_on_words_count.csv",
                                        "w",
                                        newline="",
                                    ) as f6:
                                        w = csv.writer(f6)
                                        w.writerows(trained_on_words_count.items())

                                    break

                            torch.save(crnn.state_dict(), dir + prefix + "trained_reader")
if do == 111:
    cnn = simple_CNN()
    torchinfo.summary(
        cnn,
        input_size=(1, 1, 156, 44),
    )
    adv_cnn = advanced_CNN()
    torchinfo.summary(
        adv_cnn,
        input_size=(1, 1, 156, 44),
    )

    attention = Attention(128)
    torchinfo.summary(
        attention,
        input_size=(35, 128),
    )


if do == 2:
    print("visualize featuremap")
    # char_to_int_map, int_to_char_map, char_set = read_maps()
    config = Config("char_map_short.csv", 6)

    dataset = AHTRDataset(
        "file_names-labels.csv",
        config,
        None,
        10,
    )
    loader = DataLoader(dataset, shuffle=True, batch_size=2)
    crnn = CRNN(num_classes=config.num_classes).to(device)
    crnn.load_state_dict(torch.load("scores/base/aug/" + "gru_trained_reader"))
    visualize_featuremap(crnn, loader, 1)

if do == 3:
    print("visualize model")
    config = Config("char_map_short.csv", 6)

    dataset = AHTRDataset(
        "file_names-labels.csv",
        config,
        None,
        10,
    )
    crnn = CRNN(num_classes=config.num_classes).to(device)
    crnn.load_state_dict(torch.load("scores/base/aug/" + "gru_trained_reader"))
    loader = DataLoader(dataset, shuffle=True, batch_size=2)
    visualize_model(loader, crnn)



if do == 62:
    tfs = ["scores/graph/"]
    scoring = ["testing_wer", "testing_cer", "testing_loss", "training_loss"]
    all_dict=dict()
    for tf in tfs:
        if os.path.isdir(tf):
            shutil.rmtree(tf)
        os.mkdir(tf)
        for sc in scoring:
            if os.path.isdir(tf + sc+"/"):
                shutil.rmtree(tf+sc+"/")
            os.mkdir(tf+sc+"/")

    prefix = ""
    if model == 2:
        prefix = "gru"
    elif model == 3:
        prefix = "lstm"
    elif model == 1:
        prefix = "rnn"

    dict_ = dict()
    for sc in scoring:
        for aug in augs:
            for drop in dropout:
                dr=""
                if drop==0:
                    dr=""
                else:
                    dr="drop/"

                if aug == 0:
                    dir = base_no_aug_score_dir()
                else:
                    dir = base_aug_score_dir()


                with open(dir +dr+ prefix+"_" + "list_"+sc +".pkl", "rb") as f3:
                        list_ = pickle.load(f3)

                dict_[prefix + "-"+ "dropout:"+ str(drop) +"-"+ "aug:"+ str(aug)] = list_
                all_dict[sc]=dict_
        dict_=dict()
    for key1 in all_dict:
        d = all_dict[key1]
        print(len(d))
        for key in d:
            sc_item= d[key]
            epochs = range(1, len(sc_item) + 1)
            plt.plot(epochs, sc_item, label=key)
        plt.xticks(range(1, len(sc_item) + 1))
        plt.title(key1.replace("_"," "))
        plt.xlabel("Epochs")
        plt.ylabel(key1.split("_",1)[1])
        plt.legend()
        plt.savefig(tfs[0] + key1 + "/" + "compare models.png")
        plt.show()

if do==63:
    dir="scores/base/aug/"

    with open(dir+"gru_list_testing_length_correct.pkl", "rb") as f3:
        list_ = pickle.load(f3)
    lengths= list(range(1,6))
    vals=["correct","incorrect"]

    for li in list_:
        print(li)
        for l in lengths:
            for v in vals:
                if (l,v) not in li:
                    li[(l,v)]= 0

        li=dict(sorted(li.items()))
        print(li)

    for li in list_:
    #for l in li:
        epochs = range(1, len(list_) + 1)
        plt.plot(epochs, li, label="")
    plt.xticks(range(1, len(sc_item) + 1))
    plt.title(key1.replace("_"," "))
    plt.xlabel("hs")
    plt.ylabel("")
    plt.legend()
    plt.savefig("compare models.png")
    plt.show()

    #print(list_)

if do==64:
    base_dir = "scores/base/"
    base_dir_dest = "scores/graph/"
    dir = "scores/base/aug/drop/"
    dirs =[]
    dirs.append(base_dir_dest)
    for aug in augs:
        for drop in dropout:
            if aug == 0:
                au = "no_aug/"
            else:
                au = "aug/"
            dir_ =base_dir_dest+au
            dirs.append(dir_)
            if drop == 0:
                dr = ""
            else:
                dr = "drop/"

            dir_ = dir_ + dr
            dirs.append(dir_)

    for d in dirs:
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.mkdir(d)

    for aug in augs:
        for drop in dropout:
            if drop == 0:
                dr = ""
            else:
                dr = "drop/"

            if aug == 0:
                au = "no_aug/"
            else:
                au = "aug/"
            dir= base_dir+ au+dr
            with open(dir + "gru_list_testing_length_correct.pkl", "rb") as f3:
                list_ = pickle.load(f3)
            lengths = list(range(1, 7))
            vals = ["correct", "incorrect"]

            list_dict = []

            for li in list_:
                #print(li)
                for l in lengths:
                    for v in vals:
                        if (l, v) not in li:
                            li[(l, v)] = 0

                li = dict(sorted(li.items()))
                list_dict.append(li)
                print(li)
            fig, axes = plt.subplots(nrows=2, ncols=3)
            fig.tight_layout()
            fig.subplots_adjust(bottom=0.114, left=0.088)
            kl= [[(0, 2), (2,4), (4,6)],[(6,8), (8,10), (10,12)]]
            for k in range(0, 2):
                for i in range(0,3):
                    df = pd.DataFrame(list_dict)
                    print(df.head(5))
                    x1=i*2
                    x2=i*2+2
                    df1 = df.iloc[:, kl[k][i][0]:kl[k][i][1]]
                    #plt.figure()
                    ax1 = df1.plot(ax=axes[k,i])
                    ax1.set_xticklabels(range(1, 6), rotation='horizontal')
                    ax1.set_xticks(range(0,5))
                    ax1.set_xlabel("Epoch")
                    ax1.set_ylabel("Number of words")
                    ax1.legend(loc='best')
            #fig.suptitle(' Word length, correctness ', fontsize=12)
            #plt.figure(figsize=(16, 8))

            plt.savefig(base_dir_dest+au+dr+"length.png")

            plt.show()

if do==70:
    config = Config("char_map_15.csv", 6)
    dataset = AHTRDatasetOther(
        "dirs.pkl",
        config,
        None,
        5125,
    )
    print(len(dataset))
    l=dataset[0][0]
    k=torch.from_numpy(l)

    plt.imshow(k.permute(1, 2, 0))
    plt.show()






