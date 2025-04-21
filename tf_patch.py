import tensorflow as tf
import sys

# Add compatibility layer
sys.modules['tensorflow.contrib'] = type('obj', (object,), {
    'distributions': tf.compat.v1.distributions
})