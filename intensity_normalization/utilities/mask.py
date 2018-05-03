#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
intensity_normalization.utilities.mask

create a tissue class mask of a target image

Author: Jacob Reinhold (jacob.reinhold@jhu.edu)
Created on: May 01, 2018
"""

import numpy as np
from skfuzzy import cmeans
from sklearn.mixture import GaussianMixture


def fcm_class_mask(img, brain_mask=None, hard_seg=False):
    """
    creates a mask of tissue classes for a target brain with fuzzy c-means

    Args:
        img (nibabel.nifti1.Nifti1Image): target image
        brain_mask (nibabel.nifti1.Nifti1Image): mask covering the brain of img
        hard_seg (bool): pick the maximum membership as the true class in output

    Returns:
        mask (np.ndarray): membership values for each of three classes in the image
            (or class determinations w/ hard_seg)
    """
    img_data = img.get_data()
    if brain_mask is not None:
        mask_data = brain_mask.get_data() > 0
    else:
        mask_data = img_data > 0
    [t1_cntr, t1_mem, _, _, _, _, _] = cmeans(img_data[mask_data].reshape(-1, len(mask_data[mask_data])),
                                              3, 2, 0.005, 50)
    t1_mem_list = [t1_mem[i] for i, _ in sorted(enumerate(t1_cntr), key=lambda x: x[1])]  # CSF/GM/WM
    mask = np.zeros(img_data.shape + (3,))
    for i in range(3):
        mask[..., i][mask_data] = t1_mem_list[i]
    if hard_seg:
        tmp_mask = np.zeros(img_data.shape)
        tmp_mask[mask_data] = np.argmax(mask[mask_data], axis=1) + 1
        mask = tmp_mask
    return mask


def gmm_class_mask(img, brain_mask=None, contrast='t1', return_wm_peak=True, hard_seg=False):
    """
    get a tissue class mask using gmms (or just the WM peak, for legacy use)

    Args:
        img (nibabel.nifti1.Nifti1Image): target img
        brain_mask (nibabel.nifti1.Nifti1Image): brain mask for img
        contrast (str): string to describe img's MR contrast
        return_wm_peak (bool): if true, return only the wm peak
        hard_seg (bool): if true and return_wm_peak false, then return
            hard segmentation of tissue classes

    Returns:
        if return_wm_peak true:
            wm_peak (float): represents the mean intensity for WM
        else:
            mask (np.ndarray):
                if hard_seg, then mask is the same size as img
                else, mask is the same size as img * 3, where
                the new dimensions hold the probabilities of tissue class
    """
    img_data = img.get_data()
    if brain_mask is not None:
        mask_data = brain_mask.get_data() > 0
    else:
        mask_data = img_data > 0

    brain = np.expand_dims(img_data[mask_data].flatten(), 1)
    gmm = GaussianMixture(3)
    gmm.fit(brain)

    weights = gmm.weights_
    if return_wm_peak:
        means = gmm.means_.T.squeeze()
        wm_peak = max(means) if contrast == 't1' else \
            max(zip(means, weights), key=lambda x: x[1])[0]
        return wm_peak
    else:
        classes = np.argsort(weights)
        if hard_seg:
            tmp_predicted = gmm.predict(brain)
            predicted = np.zeros(tmp_predicted.shape)
            for i, c in enumerate(classes):
                predicted[tmp_predicted == c] = i + 1
            mask = np.zeros(img_data.shape)
            mask[mask_data] = predicted + 1
        else:
            predicted_proba = gmm.predict_proba(brain)
            mask = np.zeros((*img_data.shape, 3))
            for i, c in enumerate(classes):
                mask[mask_data, i] = predicted_proba[:, c]
        return mask
