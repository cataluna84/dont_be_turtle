#-*- coding: utf-8 -*-
#! /usr/bin/env python
'''
    filename: run_load_cpktmeta_tfsummary.py
    
    description: this file is for loading the prototype model of
    pose estimation model and collecting a log summary for 
    tensorboard use in the dont-be-turtle proj.
    
    
    - functions
        - loading model from ckpt and meta files
        - collecting a summary to plotting the model in a tensorboard use.
        
    - Author : jaewook Kang @ 20180613

'''

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import tensorflow as tf

from datetime import datetime
from os import getcwd

MODULE_DIR = getcwd() + '/tfmodules'
sys.path.insert(0,MODULE_DIR)

import path_manager
import model_loader as ld

sys.path.insert(0,path_manager.EXPORT_DIR)



import_meta_filename  = '/runtrain-20180613-yglee/net.ckpt.meta'

model_loader    = ld.ModelLoader(subdir_and_filename = import_meta_filename)
model_graph_def = model_loader.load_model(clear_devices=True)


# tensorboard graph summary =============
# tensorboard config
now                 = datetime.utcnow().strftime("%Y%m%d%H%M%S")
tb_logdir           = "{}/run-{}/".format(path_manager.TENSORBOARD_DIR, now)

# summary
tb_summary_writer   = tf.summary.FileWriter(logdir=tb_logdir)
tb_summary_writer.add_graph(model_graph_def)
tb_summary_writer.close()



