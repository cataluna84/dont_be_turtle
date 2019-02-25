# Copyright 2018 Jaewook Kang (jwkang10@gmail.com) All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# -*- coding: utf-8 -*-

"""Train a dont be turtle model on GPU."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import sys
import time
import os
import json

# Setting up a min logging level to 0 
os.environ['TF_CPP_MIN_LOG_LEVEL']='0'

from absl import flags
import absl.logging as _logging  # pylint: disable=unused-import
import tensorflow as tf
import numpy as np
from datetime import datetime
from subprocess import check_output

# directory path addition
from path_manager import TF_MODULE_DIR
from path_manager import TF_MODEL_DIR
from path_manager import EXPORT_DIR
from path_manager import EXPORT_MODEL_DIR
from path_manager import TF_CNN_MODULE_DIR
from path_manager import COCO_DATALOAD_DIR

# PATH INSERSION
sys.path.insert(0,TF_MODULE_DIR)
sys.path.insert(0,TF_MODEL_DIR)
sys.path.insert(0,TF_CNN_MODULE_DIR)
sys.path.insert(0,EXPORT_DIR)
sys.path.insert(0,EXPORT_MODEL_DIR)
sys.path.insert(0,COCO_DATALOAD_DIR)


# custom python packages

### data loader
import data_loader_coco

### models
from model.model_builder import get_model
from model.model_config  import ModelConfig

#### training config
from train_config  import TrainConfig
from train_config  import PreprocessingConfig

from train_config  import FLAGS


from train_aux_fn import get_loss_heatmap
from train_aux_fn import learning_rate_schedule
from train_aux_fn import learning_rate_exp_decay
from train_aux_fn import get_heatmap_activation
from train_aux_fn import metric_fn
from train_aux_fn import summary_fn

from tensorflow.contrib.training.python.training import evaluation
from tensorflow.python.estimator import estimator


# config instance generation
train_config    = TrainConfig()
model_config    = ModelConfig()
preproc_config  = PreprocessingConfig()


train_config_dict   = train_config.__dict__
model_config_dict   = model_config.__dict__
preproc_config_dict = preproc_config.__dict__




def model_fn(features,
             labels,
             mode,
             params):
    """
    The model_fn for dontbeturtle model to be used with Estimator.
        Returns:
        A `EstimatorSpec` for the model
    """
    del params # unused

    if isinstance(features, dict):
        features = features['feature']
    if FLAGS.data_format == 'channels_first':
        assert not FLAGS.transpose_input    # channels_first only for GPU
        features = tf.transpose(features, [0, 3, 1, 2])
    if FLAGS.transpose_input and mode != tf.estimator.ModeKeys.PREDICT:
        features = tf.transpose(features, [3, 0, 1, 2])  # HWCN to NHWC


    # with tf.name_scope(name='feature_norm',values=[features]):
    #     # Standardization to the image by zero mean and unit variance.
    #     features -= tf.constant(preproc_config.MEAN_RGB,   shape=[1, 1, 3], dtype=features.dtype)
    #     features /= tf.constant(preproc_config.STDDEV_RGB, shape=[1, 1, 3], dtype=features.dtype)

    # set input_shape
    features.set_shape(features.get_shape().merge_with(
        tf.TensorShape([None,
                        model_config.input_height,
                        model_config.input_width,
                        None])))


    # Model building ============================
    # This nested function allows us to avoid duplicating the logic which
    # builds the network, for different values of --precision.
    def build_network():
        with tf.name_scope(name='build_network'):
            ''' get model '''
            out_heatmap, mid_heatmap, end_points\
                = get_model(ch_in           = features,
                            model_config    = model_config,
                            scope           = 'model')

            '''specify is_trainable on model '''
            if mode == tf.estimator.ModeKeys.TRAIN:
                model_config.hg_config.is_trainable     = True
                model_config.sv_config.is_trainable     = True
                model_config.rc_config.is_trainable     = True
                model_config.out_config.is_trainable    = True
            elif (mode == tf.estimator.ModeKeys.EVAL) or \
                    (mode == tf.estimator.ModeKeys.PREDICT):
                 model_config.hg_config.is_trainable    = False
                 model_config.sv_config.is_trainable    = False
                 model_config.rc_config.is_trainable    = False
                 model_config.out_config.is_trainable   = False

            tf.logging.info('[model_fn] feature shape=%s' % features.get_shape().as_list())
            tf.logging.info('[model_fn] labels  shape=%s' % labels.get_shape().as_list())
            tf.logging.info('[model_fn] out_heatmap  shape=%s' % out_heatmap.get_shape().as_list())
            tf.logging.info('-----------------------------------------------------------')

            for n in range(0,model_config.num_of_hgstacking - 1):
                tf.logging.info('[model_fn] mid_heatmap%d  shape=%s'
                                % (n,mid_heatmap[n].get_shape().as_list()))

                # weight init from ckpt
            if FLAGS.is_ckpt_init:
                tf.logging.info('[model_fn] ckpt loading from %s' % FLAGS.ckptinit_dir)
                tf.train.init_from_checkpoint(ckpt_dir_or_file=FLAGS.ckptinit_dir,
                                              assignment_map={"model/": "model/"})

        return out_heatmap, mid_heatmap,end_points



    # get model here
    # with tf.device('/device:GPU:0'):
    logits_out_heatmap, logits_mid_heatmap, end_points = build_network()

    #--------------------------------------------------------
    # mode == prediction case manipulation ===================
    # [[[ here need to change ]]] -----
    # if mode == tf.estimator.ModeKeys.PREDICT:
    #     predictions = {
    #
    #         # output format should be clarify here
    #         'pred_head': tf.argmax(logits_heatmap_out[-1,], axis=1),
    #         'conf_head': tf.nn.softmax(logits, name='confidence_head')
    #     }
    #
    #     # if the prediction case return here
    #     return tf.estimator.EstimatorSpec(
    #         mode=mode,
    #         predictions=predictions,
    #         export_outputs={
    #             'classify': tf.estimator.export.PredictOutput(predictions)
    #         })
    # -----------------------------

    ### output layer ===
    with tf.name_scope(name='out_post_proc', values=[logits_out_heatmap, labels]):
        # heatmap activation of output layer out
        act_out_heatmaps = get_heatmap_activation(logits=logits_out_heatmap,
                                                  scope='out_heatmap')
        # heatmap losses
        total_out_losssum = \
            get_loss_heatmap(pred_heatmaps=act_out_heatmaps,
                             label_heatmaps=labels,
                             scope='out_loss')


    ### middle layers ===
    with tf.name_scope(name='mid_post_proc', values=[logits_mid_heatmap,
                                                     labels]):
        ### supervision layers ===
        total_mid_losssum_list = []
        total_mid_losssum_acc = 0.0

        for stacked_hg_index in range(0, model_config.num_of_hgstacking - 1):
            ## heatmap activation of supervision layer out
            act_mid_heatmap_temp = \
                get_heatmap_activation(logits   =logits_mid_heatmap[stacked_hg_index],
                                       scope    ='mid_heatmap_' + str(stacked_hg_index))
            # heatmap loss
            total_mid_losssum_temp = \
                get_loss_heatmap(pred_heatmaps  =act_mid_heatmap_temp,
                                 label_heatmaps =labels,
                                 scope          ='mid_loss_' + str(stacked_hg_index))

            # collect loss and heatmap in list
            total_mid_losssum_list.append(total_mid_losssum_temp)
            total_mid_losssum_acc += total_mid_losssum_temp


    ### total loss ===
    with tf.name_scope(name='total_loss', values=[total_out_losssum,
                                                  total_mid_losssum_acc]):
        # Collect weight regularizer loss =====
        loss_regularizer = tf.losses.get_regularization_loss()
        loss = total_out_losssum + total_mid_losssum_acc + loss_regularizer




    extra_summary_hook  = None
    train_op            = None
    metric_ops          = None
    tfestimator         = None

    if mode == tf.estimator.ModeKeys.TRAIN:
        # Compute the current epoch and associated learning rate from global_step.
        global_step         = tf.train.get_global_step()
        batchnum_per_epoch  = np.floor(FLAGS.num_train_images / FLAGS.train_batch_size)

        # current_epoch       = (tf.cast(global_step, tf.float32) /
        #                         batchnum_per_epoch)
        # learning_rate       = learning_rate_schedule(current_epoch=current_epoch)
        # learning_rate       = learning_rate_exp_decay(current_epoch=current_epoch)

        learning_rate = tf.train.exponential_decay(learning_rate    =train_config.learning_rate_base,
                                                   global_step      =global_step,
                                                   decay_steps      =train_config.learning_rate_decay_step,
                                                   decay_rate       =train_config.learning_rate_decay_rate,
                                                   staircase        =True)

        optimizer           = train_config.opt_fn(learning_rate=learning_rate,
                                                   name='opt_op')

        '''
            # Batch normalization requires UPDATE_OPS to be added as a dependency to
            # the train operation.
            # when training, the moving_mean and moving_variance need to be updated.
        '''
        update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        with tf.control_dependencies(update_ops):
            train_op = optimizer.minimize(loss, global_step)

        if FLAGS.is_extra_summary:
            summary_op = summary_fn(mode                    =mode,
                                    loss                    =loss,
                                    total_out_losssum       =total_out_losssum ,
                                    total_mid_losssum_list  =total_mid_losssum_list,
                                    learning_rate           =learning_rate,
                                    input_images            =features,
                                    label_heatmap           =labels,
                                    pred_out_heatmap        =logits_out_heatmap,
                                    pred_mid_heatmap        =logits_mid_heatmap)

            tf.logging.info('Create SummarySaveHook for train')
            extra_summary_hook = tf.train.SummarySaverHook(save_steps=FLAGS.summary_step,
                                                         output_dir=FLAGS.model_dir,
                                                         summary_op=summary_op)

        # estimator instance gen
        tfestimator = tf.estimator.EstimatorSpec(mode=mode,
                                                 loss=loss,
                                                 train_op=train_op,
                                                 training_hooks=[extra_summary_hook])

    elif mode == tf.estimator.ModeKeys.EVAL:
        # in case of Estimator metric_ops must be in a form of dictionary
        tf.logging.info('Create Metric Ops')
        metric_ops          = metric_fn(labels, logits_out_heatmap, pck_threshold=FLAGS.pck_threshold)

        if FLAGS.is_extra_summary:
            summary_op = summary_fn(mode                    =mode,
                                    loss                    =loss,
                                    total_out_losssum       =total_out_losssum,
                                    input_images            =features,
                                    label_heatmap           =labels,
                                    pred_out_heatmap        =logits_out_heatmap)

            tf.logging.info('Create SummarySaveHook for eval')
            extra_summary_hook = tf.train.SummarySaverHook(save_steps=FLAGS.summary_step,
                                                         output_dir=FLAGS.model_dir+'eval/',
                                                         summary_op=summary_op)

        tfestimator = tf.estimator.EstimatorSpec(mode=mode,
                                                 loss=loss,
                                                 evaluation_hooks=[extra_summary_hook],
                                                 eval_metric_ops=metric_ops)
    else:
        tf.logging.error('[model_fn] No estimatorSpec created! ERROR')



    return tfestimator




def main(unused_argv):

    ## ckpt dir create
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    if FLAGS.is_ckpt_init:
        FLAGS.model_dir = FLAGS.ckptinit_dir
    else:
        curr_model_dir      = "{}/run-{}/".format(FLAGS.model_dir, now)
        # curr_model_dir_local= "{}/run-{}/".format(EXPORT_MODEL_DIR, now)
        FLAGS.model_dir = curr_model_dir
        if not tf.gfile.Exists(curr_model_dir):
            tf.gfile.MakeDirs(curr_model_dir)


    # if not tf.gfile.Exists(curr_model_dir_local):
    #     tf.gfile.MakeDirs(curr_model_dir_local)

    ### START: Setting up TF logger
    # get TF logger
    log = logging.getLogger('tensorflow')
    log.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # create file handler which logs even debug messages
    fh = logging.FileHandler(FLAGS.model_dir + 'tensorflow_cmd.log')
    # fh.setLevel(logging.INFO) -- Setting up logging level at the top
    fh.setFormatter(formatter)
    log.addHandler(fh)
    ### END: Setting up TF logger


    model_config.show_info()
    train_config.show_info()
    preproc_config.show_info()


    tf.logging.info('[main] data dir = %s'% FLAGS.data_dir)
    tf.logging.info('[main] model dir = %s'% FLAGS.model_dir)
    # tf.logging.info('[main] config logging dir  = %s'%curr_model_dir_local)
    tf.logging.info('------------------------')

    # # logging config information
    tf.logging.info(str(train_config_dict))
    tf.logging.info(str(model_config_dict))
    tf.logging.info(str(preproc_config_dict))

    # train_config_filename   = curr_model_dir_local + 'train_config' + '.json'
    # model_config_filename   = curr_model_dir_local + 'model_config' + '.json'
    # preproc_config_filename = curr_model_dir_local + 'preproc_config' + '.json'

    train_config_filename   = FLAGS.model_dir + 'train_config' + '.json'
    model_config_filename   = FLAGS.model_dir + 'model_config' + '.json'
    preproc_config_filename = FLAGS.model_dir + 'preproc_config' + '.json'


    with open(train_config_filename, 'a') as fp:
        json.dump(str(train_config_dict), fp)

    with open(model_config_filename, 'a') as fp:
        json.dump(str(model_config_dict), fp)

    with open(preproc_config_filename, 'a') as fp:
        json.dump(str(preproc_config_dict), fp)


    # try:
    #     cmd = "sudo gsutil cp -r {} {}".format(curr_model_dir_local + '* ', curr_model_dir)
    #     print ('[main] cmd=%s'%cmd)
    #     check_output(cmd,shell=True)
    #     tf.logging.info('[main] success logging config in bucket')
    # except:
    #     tf.logging.info('[main] failure logging config in bucket')


    # for CPU or GPU use
    config = tf.ConfigProto(allow_soft_placement=True,
                            log_device_placement=False,
                            gpu_options=tf.GPUOptions(allow_growth=True))


    config = tf.estimator.RunConfig(
                model_dir                       =FLAGS.model_dir,
                tf_random_seed                  =None,
                save_summary_steps              =FLAGS.summary_step,
                save_checkpoints_steps          =max(600, FLAGS.iterations_per_loop),
                session_config                  = config,
                keep_checkpoint_max             =5,
                keep_checkpoint_every_n_hours   =10000,
                log_step_count_steps            =FLAGS.log_step_count_steps,
                train_distribute                =None)

    dontbeturtle_estimator  = tf.estimator.Estimator(
                model_dir          = FLAGS.model_dir,
                model_fn           = model_fn,
                config             = config,
                params             = None,
                warm_start_from    = None)

    '''
    # data loader
    # Input pipelines are slightly different (with regards to shuffling and
    # preprocessing) between training and evaluation.
    '''
    dataset_train, dataset_eval = \
        [data_loader_coco.DataSetInput(
        is_training     =is_training,
        data_dir        =FLAGS.data_dir,
        transpose_input =FLAGS.transpose_input,
        use_bfloat16    =False) for is_training in [True, False]]



    if FLAGS.mode == 'eval':
        eval_steps = FLAGS.num_eval_images // FLAGS.eval_batch_size

        # Run evaluation when there's a new checkpoint
        for ckpt in evaluation.checkpoints_iterator(
                FLAGS.model_dir, timeout=FLAGS.eval_timeout):
            tf.logging.info('Starting to evaluate.')

            try:
                start_timestamp = time.time()  # This time will include compilation time
                eval_results = dontbeturtle_estimator.evaluate(
                    input_fn        =dataset_eval.input_fn,
                    steps           =eval_steps,
                    checkpoint_path =ckpt)

                elapsed_time = int(time.time() - start_timestamp)
                tf.logging.info('Eval results: %s. Elapsed seconds: %d' %
                                (eval_results, elapsed_time))

                # Terminate eval job when final checkpoint is reached
                current_step = int(os.path.basename(ckpt).split('-')[1])
                if current_step >= FLAGS.train_steps:
                    tf.logging.info(
                      'Evaluation finished after training step %d' % current_step)
                    break

            except tf.errors.NotFoundError:
                # Since the coordinator is on a different job than the GPU worker,
                # sometimes the GPU worker does not finish initializing until long after
                # the CPU job tells it to start evaluating. In this case, the checkpoint
                # file could have been deleted already.
                tf.logging.info(
                    'Checkpoint %s no longer exists, skipping checkpoint' % ckpt)

    else:   # FLAGS.mode == 'train' or FLAGS.mode == 'train_and_eval'
        current_step = estimator._load_global_step_from_checkpoint_dir(FLAGS.model_dir)     # pylint: disable=protected-access,line-too-long
        batchnum_per_epoch = FLAGS.num_train_images // FLAGS.train_batch_size

        tf.logging.info('[main] num_train_images=%s' % FLAGS.num_train_images)
        tf.logging.info('[main] train_batch_size=%s' % FLAGS.train_batch_size)
        tf.logging.info('[main] batchnum_per_epoch=%s' % batchnum_per_epoch)
        tf.logging.info('[main] Training for %d steps (%.2f epochs in total). Current'
                        ' step %d.' % (FLAGS.train_steps,
                                       FLAGS.train_steps / batchnum_per_epoch,
                                       current_step))

        start_timestamp = time.time()  # This time will include compilation time

        if FLAGS.mode == 'train':
            tf.logging.info('[main] Training only')

            dontbeturtle_estimator.train(
                input_fn    =dataset_train.input_fn,
                max_steps   =FLAGS.train_steps)
            
        else:
            assert FLAGS.mode == 'train_and_eval'
            tf.logging.info('[main] Training and Evaluation')

            while current_step < FLAGS.train_steps:
                # Train for up to steps_per_eval number of steps.
                # At the end of training, a checkpoint will be written to --model_dir.
                next_checkpoint = min(current_step + FLAGS.steps_per_eval,
                                      FLAGS.train_steps)
                dontbeturtle_estimator.train(
                    input_fn    =dataset_train.input_fn,
                    max_steps   =next_checkpoint)

                current_step = next_checkpoint

                # Evaluate the model on the most recent model in --model_dir.
                # Since evaluation happens in batches of --eval_batch_size, some images
                # may be consistently excluded modulo the batch size.
                tf.logging.info('Starting to evaluate.')
                eval_results    = dontbeturtle_estimator.evaluate(
                    input_fn    =dataset_eval.input_fn,
                    steps       =FLAGS.num_eval_images // FLAGS.eval_batch_size)

                tf.logging.info('Eval results: %s' % eval_results)

                elapsed_time = int(time.time() - start_timestamp)
                tf.logging.info('Finished training up to step %d. Elapsed seconds %d.' %
                        (FLAGS.train_steps, elapsed_time))

        # if FLAGS.export_dir is not None:
        #     # The guide to serve a exported TensorFlow model is at:
        #     #    https://www.tensorflow.org/serving/serving_basic
        #     tf.logging.info('Starting to export model.')
        #     dontbeturtle_estimator.export_savedmodel(
        #         export_dir_base             =FLAGS.export_dir,
        #         serving_input_receiver_fn   =data_loader_tpu.image_serving_input_fn)



if __name__ == '__main__':
    

    # file_handler = logging.FileHandler(filename='tensorflow_run.log')
    # stdout_handler = logging.StreamHandler(sys.stdout)
    # handlers = [file_handler, stdout_handler]
    # logging.basicConfig(
    #     level=logging.INFO, 
    #     format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    #     handlers=handlers
    # )
    # logger = logging.getLogger('tensorflow')
    
    # tf.logging.set_verbosity(tf.logging.INFO)
    
    tf.app.run()
