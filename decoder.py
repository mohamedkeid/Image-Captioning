import torch
import torch.nn as nn
import torch.nn.functional as F
from attention import Attention
from torch.autograd import Variable


class DecoderRNN(nn.Module):
    def __init__(self, attention_method, hidden_size, output_size, n_layers=1, dropout_p=.1):
        super(DecoderRNN, self).__init__()

        # Keep parameters
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.n_layers = n_layers
        self.dropout_p = dropout_p

        # Define layers
        self.embedding = nn.Embedding(output_size, hidden_size)
        self.lstm = nn.LSTM(hidden_size * 2, hidden_size, n_layers, dropout=dropout_p)
        self.out = nn.Linear(hidden_size * 2, output_size)

        # Choose attention model
        if attention_method is not None:
            self.attention = Attention(attention_method, hidden_size)

    # Run forward propagation one step at a time
    def forward(self, word_input, last_context, last_h, last_c, image_maps):
        # Get embedding of current input word (last output word) (s = 1 x batch_size x seq_len)
        word_embedded = self.embedding(word_input).view(1, 1, -1)

        # Combine embedded input word and last context, run through rnn
        rnn_input = torch.cat((word_embedded, last_context.unsqueeze(0)), 2)
        rnn_output, rnn_states = self.lstm(rnn_input, (last_h, last_c))
        h, c = rnn_states

        # Calculate attention from current RNN state and encoded image feature maps
        attention_weights = self.attention(rnn_output.squeeze(0), image_maps)
        image_maps = image_maps.view(-1, 1, self.hidden_size)
        context = attention_weights.bmm(image_maps.transpose(0, 1))

        # Final output layer (next word prediction using rnn hidden state and context vector)
        rnn_output = rnn_output.squeeze(0)
        context = context.squeeze(1)
        output = F.log_softmax(self.out(torch.cat((rnn_output, context), 1)))

        return output, context, h, c, attention_weights

    def init_hidden(self):
        hidden = Variable(torch.zeros(self.n_layers, 1, self.hidden_size))
        hidden = hidden.cuda()

        return hidden
