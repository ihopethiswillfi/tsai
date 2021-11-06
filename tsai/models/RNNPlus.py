# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/105_models.RNNPlus.ipynb (unless otherwise specified).

__all__ = ['RNNPlus', 'LSTMPlus', 'GRUPlus']

# Cell
from ..imports import *
from ..utils import *
from ..data.core import *
from .layers import *

# Cell
class _RNN_Backbone(Module):
    def __init__(self, cell, c_in, c_out, seq_len=None, hidden_size=100, n_layers=1, bias=True, rnn_dropout=0, bidirectional=False,
                 n_embeds=None, embed_dims=None, cat_pos=None, feature_extractor=None, init_weights=True):

        # Categorical embeddings
        if n_embeds is not None:
            self.to_cat_embed = MultiEmbeddding(c_in, n_embeds, embed_dims=embed_dims, cat_pos=cat_pos)
            if embed_dims is None:
                embed_dims = [emb_sz_rule(s) for s in n_embeds]
            c_in = c_in + sum(embed_dims) - len(n_embeds)
        else:
            self.to_cat_embed = nn.Identity()

        # Feature extractor
        if feature_extractor:
            assert isinstance(feature_extractor, nn.Module), "feature extractor must be an nn.Module"
            self.feature_extractor = feature_extractor
            c_in, seq_len = self._calculate_output_size(self.feature_extractor, c_in, seq_len)
        else:
            self.feature_extractor = nn.Identity()

        # RNN layers
        rnn_layers = []
        if len(set(hidden_size)) == 1:
            hidden_size = hidden_size[0]
            if n_layers == 1: rnn_dropout = 0
            rnn_layers.append(cell(c_in, hidden_size, num_layers=n_layers, bias=bias, batch_first=True, dropout=rnn_dropout, bidirectional=bidirectional))
            rnn_layers.append(LSTMOutput()) # this selects just the output, and discards h_n, and c_n
        else:
            for i in range(len(hidden_size)):
                input_size = c_in if i == 0 else hs * (1 + bidirectional)
                hs = hidden_size[i]
                rnn_layers.append(cell(input_size, hs, num_layers=1, bias=bias, batch_first=True, bidirectional=bidirectional))
                rnn_layers.append(LSTMOutput()) # this selects just the output, and discards h_n, and c_n
                if rnn_dropout and i < len(hidden_size) - 1: rnn_layers.append(nn.Dropout(rnn_dropout)) # add dropout to all layers except last
        self.rnn = nn.Sequential(*rnn_layers)
        self.transpose = Transpose(-1, -2, contiguous=True)
        if init_weights: self.apply(self._weights_init)

    def forward(self, x):
        x = self.to_cat_embed(x)
        x = self.feature_extractor(x)
        x = self.transpose(x)                    # [batch_size x n_vars x seq_len] --> [batch_size x seq_len x n_vars]
        x = self.rnn(x)                          # [batch_size x seq_len x hidden_size * (1 + bidirectional)]
        x = self.transpose(x)                    # [batch_size x hidden_size * (1 + bidirectional) x seq_len]
        return x

    def _weights_init(self, m):
        # same initialization as keras. Adapted from the initialization developed
        # by JUN KODA (https://www.kaggle.com/junkoda) in this notebook
        # https://www.kaggle.com/junkoda/pytorch-lstm-with-tensorflow-like-initialization
        for name, params in m.named_parameters():
            if "weight_ih" in name:
                nn.init.xavier_normal_(params)
            elif 'weight_hh' in name:
                nn.init.orthogonal_(params)
            elif 'bias_ih' in name:
                params.data.fill_(0)
                # Set forget-gate bias to 1
                n = params.size(0)
                params.data[(n // 4):(n // 2)].fill_(1)
            elif 'bias_hh' in name:
                params.data.fill_(0)

    @torch.no_grad()
    def _calculate_output_size(self, m, c_in, seq_len):
        xb = torch.randn(1, c_in, seq_len)
        c_in, seq_len = m(xb).shape[1:]
        return c_in, seq_len

# Cell
class _RNNPlus_Base(nn.Sequential):
    def __init__(self, c_in, c_out, seq_len=None, hidden_size=[100], n_layers=1, bias=True, rnn_dropout=0, bidirectional=False,
                 n_embeds=None, embed_dims=None, cat_pos=None, feature_extractor=None, fc_dropout=0., last_step=True, bn=False,
                 custom_head=None, y_range=None, init_weights=True):

        if not last_step: assert seq_len, 'you need to enter a seq_len to use flatten=True'

        # Backbone
        hidden_size = listify(hidden_size)
        backbone = _RNN_Backbone(self._cell, c_in, c_out, seq_len=seq_len, hidden_size=hidden_size, n_layers=n_layers,
                                 n_embeds=n_embeds, embed_dims=embed_dims, cat_pos=cat_pos, feature_extractor=feature_extractor,
                                 bias=bias, rnn_dropout=rnn_dropout,  bidirectional=bidirectional, init_weights=init_weights)

        # Head
        self.head_nf = hidden_size * (1 + bidirectional) if isinstance(hidden_size, Integral) else hidden_size[-1] * (1 + bidirectional)
        if custom_head:
            if isinstance(custom_head, nn.Module): head = custom_head
            else: head = custom_head(self.head_nf, c_out, seq_len)
        else: head = self.create_head(self.head_nf, c_out, seq_len, last_step=last_step, fc_dropout=fc_dropout, bn=bn, y_range=y_range)
        super().__init__(OrderedDict([('backbone', backbone), ('head', head)]))

    def create_head(self, nf, c_out, seq_len, last_step=True, fc_dropout=0., bn=False, y_range=None):
        if last_step:
            layers = [LastStep()]
        else:
            layers = [Flatten()]
            nf *= seq_len
        if bn: layers += [nn.BatchNorm1d(nf)]
        if fc_dropout: layers += [nn.Dropout(fc_dropout)]
        layers += [nn.Linear(nf, c_out)]
        if y_range: layers += [SigmoidRange(*y_range)]
        return nn.Sequential(*layers)


class RNNPlus(_RNNPlus_Base):
    _cell = nn.RNN

class LSTMPlus(_RNNPlus_Base):
    _cell = nn.LSTM

class GRUPlus(_RNNPlus_Base):
    _cell = nn.GRU