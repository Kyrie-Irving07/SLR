import tensorflow as tf


def set_conv(X, W_shape, out_dim, stride, scope=None, activate="relu"):
    with tf.variable_scope(scope or 'conv', reuse=tf.AUTO_REUSE):
        X = tf.contrib.layers.batch_norm(X, 0.9, epsilon=1e-5, activation_fn=tf.nn.relu)
        W = tf.get_variable('W', [W_shape, W_shape, X.get_shape().as_list()[3], out_dim], trainable=True, initializer=tf.random_normal_initializer(mean=0, stddev=0.1))
        b = tf.get_variable('b', out_dim, trainable=True, initializer=tf.random_normal_initializer)
        out = tf.nn.bias_add(tf.nn.conv2d(X, W, strides=[1, stride, stride, 1], padding='SAME'), b)
        if activate == "relu":
            out = tf.nn.leaky_relu(out)
        elif activate == "sigmoid":
            out = tf.nn.sigmoid(out)
        else:
            raise NotADirectoryError
        return out


def set_deconv(X, W_shape, out_dim, stride, batch_size, scope=None, activate=tf.nn.leaky_relu):
    with tf.variable_scope(scope or 'conv', reuse=tf.AUTO_REUSE):
        output_shape = [batch_size, X.get_shape().as_list()[1] * stride, X.get_shape().as_list()[2] * stride, out_dim]
        X = tf.contrib.layers.batch_norm(X, 0.9, epsilon=1e-5, activation_fn=tf.nn.relu)
        W = tf.get_variable('W', [W_shape, W_shape, out_dim, X.get_shape().as_list()[3]], trainable=True, initializer=tf.random_normal_initializer(mean=0, stddev=0.1))
        b = tf.get_variable('b', out_dim, trainable=True, initializer=tf.random_normal_initializer)
        out = tf.nn.bias_add(tf.nn.conv2d_transpose(X, W, output_shape=output_shape, strides=[1, stride, stride, 1], padding='SAME'), b)
        out = activate(out)
        return out


def set_full(X, out_dim, scope=None, activate=tf.nn.relu):
    with tf.variable_scope(scope or 'full', reuse=tf.AUTO_REUSE):
        W = tf.get_variable('W', [X.get_shape().as_list()[1], out_dim], trainable=True, initializer=tf.random_normal_initializer(mean=0, stddev=0.1))
        b = tf.get_variable('b', [out_dim], trainable=True, initializer=tf.random_normal_initializer)
        output = tf.add(tf.tensordot(X, W, [[1], [0]]), b)
        if activate:
            output = activate(output)
        return output


def set_res(input, out_dim, scope):
    with tf.variable_scope(scope or 'res_momdule', reuse=tf.AUTO_REUSE):
        skip = set_conv(X=input, W_shape=1, out_dim=out_dim, stride=1, scope=scope+'_skip_')

        res = set_conv(X=input, W_shape=1, out_dim=out_dim/2, stride=1, scope=scope+'_res0_')
        res = set_conv(X=res, W_shape=3, out_dim=out_dim/2, stride=1, scope=scope+'_res1_')
        res = set_conv(X=res, W_shape=1, out_dim=out_dim, stride=1, scope=scope+'_res2_')

        return tf.add(res, skip)


def set_hourglass(input, layers, out_dim, scope=None):
    with tf.variable_scope(scope or 'hourglass', reuse=tf.AUTO_REUSE):
        if layers == 0:
            output = set_res(input=input, out_dim=out_dim, scope='res_module0')
        else:
            conv_out = set_res(input=input, out_dim=out_dim, scope='res_module'+str(layers))
            res_out = tf.nn.max_pool(conv_out, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
            res_out = set_hourglass(input=res_out, layers=layers-1, out_dim=out_dim, scope=scope)
            res_out = tf.image.resize_nearest_neighbor(res_out, tf.shape(res_out)[1:3]*2, name='up_sample')
            output = tf.add(conv_out, res_out)
    return output


def set_3dconv(X, depth, W_shape, out_dim, stride, scope=None, activate="relu"):
    with tf.variable_scope(scope or 'conv', reuse=tf.AUTO_REUSE):
        X = tf.contrib.layers.batch_norm(X, 0.9, epsilon=1e-5, activation_fn=tf.nn.relu)
        W = tf.get_variable('W', [depth, W_shape, W_shape, X.get_shape().as_list()[4], out_dim], trainable=True, initializer=tf.random_normal_initializer)
        b = tf.get_variable('b', out_dim, trainable=True, initializer=tf.random_normal_initializer)
        out = tf.nn.conv3d(X, W, strides=[1, 1, stride, stride, 1], padding='SAME')
        out = tf.nn.bias_add(out, b)
        if activate == "relu":
            out = tf.nn.leaky_relu(out)
        elif activate == "sigmoid":
            out = tf.nn.sigmoid(out)
        else:
            raise NotADirectoryError
        return out


def set_cnn(input, depth, W_shape, channel, out_dim=1024, scope=None):
    with tf.variable_scope(scope or 'cnn', reuse=tf.AUTO_REUSE):
        for i in range(len(channel)):
            input = set_3dconv(input, depth, W_shape, channel[i], 1, 'cov' + str(i))
            input = tf.nn.max_pool3d(input, ksize=[1, 1, 2, 2, 1], strides=[1, 1, 2, 2, 1], padding='SAME')
        shape = input.get_shape().as_list()
        output = tf.reshape(input, [-1, shape[2]*shape[3]*shape[4]])
        output = set_full(output, out_dim, 'fully_connection')
        return output
