import argparse
import etl
import helpers
import random
import time
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.models as models
from decoder import DecoderRNN
from torch.autograd import Variable

parser = argparse.ArgumentParser()
parser.add_argument('--dropout_p', default=.05)
parser.add_argument('--epochs', default=50000)
parser.add_argument('--grad_clip', default=.5)
parser.add_argument('--learning_rate', default=.0001)
parser.add_argument('--n_layers', default=2)
parser.add_argument('--plot_every', default=200)
parser.add_argument('--print_every', default=100)
parser.add_argument('--teacher_forcing_ratio', default=.5)
args = parser.parse_args()


def train(input_var, target_var, encoder, decoder, decoder_opt, criterion):
    # Initialize optimizer and loss
    decoder_opt.zero_grad()
    loss = 0.
    s = input_var.size()

    # Get target sequence length
    target_length = target_var.size()[0]

    # Prepare input and output variables
    decoder_input = Variable(torch.LongTensor([0]))
    decoder_input = decoder_input.cuda()
    decoder_context = Variable(torch.zeros(1, decoder.hidden_size))
    decoder_context = decoder_context.cuda()
    decoder_hidden = decoder.init_hidden()

    # Scheduled sampling
    use_teacher_forcing = random.random() < args.teacher_forcing_ratio
    if use_teacher_forcing:
        # Feed target as the next input
        for di in range(target_length):
            decoder_output, decoder_context, decoder_hidden, decoder_attention = decoder(decoder_input,
                                                                                         decoder_context,
                                                                                         decoder_hidden,
                                                                                         input_var)
            loss += criterion(decoder_output[0], target_var[di])
            decoder_input = target_var[di]

    else:
        # Use previous prediction as next input
        for di in range(target_length):
            decoder_output, decoder_context, decoder_hidden, decoder_attention = decoder(decoder_input,
                                                                                         decoder_context,
                                                                                         decoder_hidden,
                                                                                         input_var)
            loss += criterion(decoder_output[0], target_var[di])

            topv, topi = decoder_output.data.topk(1)
            ni = topi[0][0]

            decoder_input = Variable(torch.LongTensor([[ni]]))
            decoder_input = decoder_input.cuda()

            if ni == 1:
                break

    # Backpropagation
    loss.backward()
    torch.nn.utils.clip_grad_norm(decoder.parameters(), args.grad_clip)
    decoder_opt.step()

    return loss.data[0] / target_length

# Initialize models
lang = etl.prepare_data()
encoder = models.vgg16(pretrained=True)
decoder = DecoderRNN('general', 128, lang.n_words, args.n_layers, dropout_p=args.dropout_p)

# Make sure we do not train our encoder net
for param in encoder.parameters():
    param.requires_grad = False

# Move models to GPU
encoder.cuda()
decoder.cuda()

# Initialize optimizers and criterion
learning_rate = 0.0001
decoder_optimizer = optim.Adam(decoder.parameters(), lr=learning_rate)
criterion = nn.NLLLoss()

# Keep track of time elapsed and running averages
start = time.time()
plot_losses = []
print_loss_total = 0 # Reset every print_every
plot_loss_total = 0 # Reset every plot_every

# Begin training
for epoch in range(1, args.epochs + 1):

    # Get training data for this cycle
    input_variable, target_variable = etl.get_example(lang, encoder, epoch - 1)

    # Run the train step
    loss = train(input_variable, target_variable, encoder, decoder, decoder_optimizer, criterion)

    # Keep track of loss
    print_loss_total += loss
    plot_loss_total += loss

    if epoch == 0:
        continue

    if epoch % args.print_every == 0:
        print_loss_avg = print_loss_total / args.print_every
        print_loss_total = 0
        time_since = helpers.time_since(start, epoch / args.epochs)
        print('%s (%d %d%%) %.4f' % (time_since, epoch, epoch / args.epochs * 100, print_loss_avg))

    if epoch % args.plot_every == 0:
        plot_loss_avg = plot_loss_total / args.plot_every
        plot_losses.append(plot_loss_avg)
        plot_loss_total = 0

# Save our models
torch.save(decoder.state_dict(), 'data/decoder_params')
torch.save(decoder.attention.state_dict(), 'data/attention_params')

# Plot loss
helpers.show_plot(plot_losses)
