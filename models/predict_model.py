import torch
import os
import json
from collections import OrderedDict
import torch.nn.functional as F
from models.base_model import BaseModel
from models.networks.fc import FcEncoder
from models.networks.lstm import LSTMEncoder
from models.networks.textcnn import TextCNN
from models.networks.classifier import FcClassifier, Fusion
from models.networks.autoencoder_2 import ResidualAE
from models.networks.autoencoder_2 import MultiClassifyEncoder
# from models.networks.autoencoder import ResidualAE
from models.networks.multihead_attention import MultiheadAttention
from models.networks.interact_model import InteractModule
from models.utils.config import OptConfig
import math
import numpy as np


class PredictModel(BaseModel):
    @staticmethod
    def modify_commandline_options(parser, is_train=True):
        parser.add_argument('--input_dim_a', type=int, default=130, help='acoustic input dim')
        parser.add_argument('--input_dim_l', type=int, default=1024, help='lexical input dim')
        parser.add_argument('--input_dim_v', type=int, default=384, help='lexical input dim')
        parser.add_argument('--embd_size_a', default=128, type=int, help='audio model embedding size')
        parser.add_argument('--embd_size_l', default=128, type=int, help='text model embedding size')
        parser.add_argument('--embd_size_v', default=128, type=int, help='visual model embedding size')
        parser.add_argument('--embd_method_a', default='maxpool', type=str, choices=['last', 'maxpool', 'attention'], \
                            help='audio embedding method,last,mean or atten')
        parser.add_argument('--embd_method_v', default='maxpool', type=str, choices=['last', 'maxpool', 'attention'], \
                            help='visual embedding method,last,mean or atten')
        parser.add_argument('--AE_layers', type=str, default='128,64,32',
                            help='256,128 for 2 layers with 256, 128 nodes respectively')
        parser.add_argument('--n_blocks', type=int, default=3, help='number of AE blocks')
        parser.add_argument('--cls_layers', type=str, default='128,128',
                            help='256,128 for 2 layers with 256, 128 nodes respectively')
        parser.add_argument('--dropout_rate', type=float, default=0.3, help='rate of dropout')
        parser.add_argument('--bn', action='store_true', help='if specified, use bn layers in FC')
        parser.add_argument('--data_path', type=str,
                            help='where to load dataset')
        parser.add_argument('--ce_weight', type=float, default=1.0, help='weight of ce loss')
        parser.add_argument('--cl_weight', type=float, default=1.0, help='weight of cl loss')
        parser.add_argument('--mse_weight', type=float, default=1.0, help='weight of mse loss')
        parser.add_argument('--nhead', type=int, default=1, help='head of multi-head attention')
        parser.add_argument('--attention_head', type=int, default=1, help='head of multi-head attention')
        parser.add_argument('--attention_dropout', type=float, default=0., help='head of multi-head attention')
        parser.add_argument('--temperature', type=float, default=0.007, help='temperature of contrastive learning loss')
        parser.add_argument('--activate_fun', type=str, default='relu', help='which activate function will be used')
        parser.add_argument('--ablation', type=str, default='normal', help='which module should be ablate')
        parser.add_argument('--pretrained_path', type=str, help='where to load pretrained encoder network')

        return parser

    def __init__(self, opt):
        """Initialize the LSTM autoencoder class
        Parameters:
            opt (Option class)-- stores all the experiment flags; needs to be a subclass of BaseOptions
        """
        super().__init__(opt)
        # our expriment is on 10 fold setting, teacher is on 5 fold setting, the train set should match
        self.loss_names = []
        self.model_names = []  # 所有模块的名称

        # acoustic model
        self.netEmoA = LSTMEncoder(opt.input_dim_a, opt.embd_size_a, embd_method=opt.embd_method_a)
        self.model_names.append('EmoA')

        # lexical model
        self.netEmoL = TextCNN(opt.input_dim_l, opt.embd_size_l, dropout=0.5)
        self.model_names.append('EmoL')

        # visual model
        self.netEmoV = LSTMEncoder(opt.input_dim_v, opt.embd_size_v, opt.embd_method_v)
        self.model_names.append('EmoV')

        # Transformer Fusion model
        emo_encoder_layer = torch.nn.TransformerEncoderLayer(d_model=opt.hidden_size, nhead=int(opt.nhead))
        self.netEmoFusion = torch.nn.TransformerEncoder(emo_encoder_layer, num_layers=opt.nhead)
        self.model_names.append('EmoFusion')

        # Classifier
        cls_layers = list(map(lambda x: int(x), opt.cls_layers.split(',')))
        cls_input_size = 2 * opt.hidden_size
        self.netEmoC = FcClassifier(cls_input_size, cls_layers, output_dim=opt.emo_output_dim, dropout=opt.dropout_rate,
                                    use_bn=opt.bn)
        self.model_names.append('EmoC')
        self.loss_names.append('emo_CE')
        self.netEmoCA = FcClassifier(opt.hidden_size, cls_layers, output_dim=opt.emo_output_dim,
                                     dropout=opt.dropout_rate,
                                     use_bn=opt.bn)
        self.model_names.append('EmoCA')
        self.loss_names.append('EmoA_CE')
        self.netEmoCV = FcClassifier(opt.hidden_size, cls_layers, output_dim=opt.emo_output_dim,
                                     dropout=opt.dropout_rate,
                                     use_bn=opt.bn)
        self.model_names.append('EmoCV')
        # self.loss_names.append('EmoV_CE')
        self.netEmoCL = FcClassifier(opt.hidden_size, cls_layers, output_dim=opt.emo_output_dim,
                                     dropout=opt.dropout_rate,
                                     use_bn=opt.bn)
        self.model_names.append('EmoCL')
        self.loss_names.append('EmoL_CE')

        self.netPA = torch.nn.Linear(512, 130)
        self.model_names.append('PA')

        self.netPV = torch.nn.Linear(1024, 342)
        self.model_names.append('PV')

        self.netPL = torch.nn.Linear(768, 1024)
        self.model_names.append('PL')

        self.temperature = opt.temperature

        if self.isTrain:
            self.load_pretrained_encoder(opt)
            self.criterion_ce = torch.nn.CrossEntropyLoss()
            # initialize optimizers; schedulers will be automatically created by function <BaseModel.setup>.
            paremeters = [{'params': getattr(self, 'net' + net).parameters()} for net in self.model_names]
            self.optimizer = torch.optim.Adam(paremeters, lr=opt.lr, betas=(opt.beta1, 0.999))
            self.optimizers.append(self.optimizer)
            self.emo_output_dim = opt.emo_output_dim
            self.int_output_dim = opt.int_output_dim
            self.ce_weight = opt.ce_weight
            self.mse_weight = opt.mse_weight
            self.cl_weight = opt.cl_weight
        else:
            self.load_pretrained_encoder(opt)

        # modify save_dir
        self.save_dir = os.path.join(self.save_dir, str(opt.cvNo))
        print(self.save_dir)
        if not os.path.exists(self.save_dir):
            os.mkdir(self.save_dir)

    # 加载预训练Encoder，
    def load_pretrained_encoder(self, opt):
        print('Init parameter from {}'.format('None'))
        # print('Init parameter from {}'.format(opt.pretrained_path))
        # pretrained_path = os.path.join(opt.pretrained_path, str(opt.cvNo))
        # pretrained_config_path = os.path.join(opt.pretrained_path, 'train_opt.conf')
        # pretrained_config = self.load_from_opt_record(pretrained_config_path)
        # pretrained_config.isTrain = False                             # teacher model should be in test mode
        # pretrained_config.gpu_ids = opt.gpu_ids                       # set gpu to the same
        # self.pretrained_encoder = pretrainModel(pretrained_config)
        # self.pretrained_encoder.load_networks_cv(pretrained_path)
        # self.pretrained_encoder.cuda()
        # self.pretrained_encoder.eval()

    def load_from_opt_record(self, file_path):
        opt_content = json.load(open(file_path, 'r'))
        opt = OptConfig()
        opt.load(opt_content)
        return opt

    def set_input(self, input):
        """
        Unpack input data from the dataloader and perform necessary pre-processing steps.
        Parameters:
            input (dict): include the data itself and its metadata information.
        """
        # MOSEI 数据维度：A:74;V:35;T300
        # IEMOCAP 数据维度：A:130;V:342;T:1024
        self.acoustic = input['A_feat'].float().to(self.device)
        self.lexical = input['L_feat'].float().to(self.device)
        self.visual = input['V_feat'].float().to(self.device)

        # Emotion label
        self.emo_label = input['emo_label'].to(self.device)

        # self.emo_target_labels = input['emo_target_labels']
        # for i in range(len(self.emo_target_labels)):
        #     self.emo_target_labels[i] = self.emo_target_labels[i].to(self.device)

    def forward(self):
        """Run forward pass; called by both functions <optimize_parameters> and <test>."""
        # get utt level representattion
        # if not self.isTrain :
        #     self.acoustic = self.netPA(self.acoustic)
        #     self.lexical = self.netPL(self.lexical)
        #     self.visual = self.netPV(self.visual)

        emo_feat_A = self.netEmoA(self.acoustic)
        emo_feat_L = self.netEmoL(self.lexical)
        # emo_feat_V = self.netEmoV(self.visual)

        emo_fusion_feat = torch.stack((emo_feat_A, emo_feat_L), dim=0)
        emo_fusion_feat = self.netEmoFusion(emo_fusion_feat)

        # print(f'emo_fusion_feat_no_cat.shape is {emo_fusion_feat.shape}')
        emo_fusion_feat = torch.cat((emo_fusion_feat[0], emo_fusion_feat[1]), dim=1)

        # uni-modal prediction
        self.emo_logits_a, _ = self.netEmoCA(emo_feat_A)
        self.emo_logits_l, _ = self.netEmoCL(emo_feat_L)
        # self.emo_logits_v, _ = self.netEmoCV(emo_feat_V)

        # emotion prediction
        self.emo_logits, _ = self.netEmoC(emo_fusion_feat)
        # self.emo_logits = self.emo_logits_a


        self.emo_pred = F.softmax(self.emo_logits, dim=-1)
        # self.int_pred = F.softmax(self.int_logits, dim=-1)
        self.int_pred = self.emo_pred

    def backward(self):
        """Calculate the loss for back propagation"""
        # print(r'Calculate the loss for back propagation')
        #
        self.loss_emo_CE = self.ce_weight * self.criterion_ce(self.emo_logits, self.emo_label)
        #
        self.loss_EmoA_CE = self.criterion_ce(self.emo_logits_a, self.emo_label)
        self.loss_EmoL_CE = self.criterion_ce(self.emo_logits_l, self.emo_label)
        # self.loss_EmoV_CE = self.criterion_ce(self.emo_logits_v, self.emo_label)
        #
        # loss = self.loss_emo_CE + self.loss_int_CE + self.loss_IntA_CE + self.loss_IntL_CE + self.loss_IntV_CE + self.loss_EmoL_CE + self.loss_EmoA_CE + self.loss_EmoV_CE
        loss = self.loss_emo_CE + self.loss_EmoA_CE + self.loss_EmoL_CE # + self.loss_EmoV_CE

        loss.backward()
        for model in self.model_names:
            torch.nn.utils.clip_grad_norm_(getattr(self, 'net' + model).parameters(), 1.0)


    def optimize_parameters(self, epoch):
        """Calculate losses, gradients, and update network weights; called in every training iteration"""
        # forward
        self.forward()
        # print('forward has done')
        # backward
        self.optimizer.zero_grad()
        self.backward()
        # print('backward has done')
        self.optimizer.step()


class ActivateFun(torch.nn.Module):
    def __init__(self, opt):
        super(ActivateFun, self).__init__()
        self.activate_fun = opt.activate_fun

    def _gelu(self, x):
        return x * 0.5 * (1.0 + torch.erf(x / math.sqrt(2.0)))

    def forward(self, x):
        if self.activate_fun == 'relu':
            return torch.relu(x)
        elif self.activate_fun == 'gelu':
            return self._gelu(x)
