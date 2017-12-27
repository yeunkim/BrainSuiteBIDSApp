# -*- coding: utf-8 -*-
"""
Author: Jason Wong
Edit: Yeun Kim
"""
from __future__ import unicode_literals, print_function

from nipype import config #Set configuration before importing nipype pipeline
from nipype.interfaces.utility import Function
cfg = dict(execution={'remove_unnecessary_outputs' : False}) #We do not want nipype to remove unnecessary outputs
config.update_config(cfg)

import nipype.pipeline.engine as pe
import nipype.interfaces.brainsuite as bs
import nipype.interfaces.io as io
import os
from bids.grabbids import BIDSLayout
from shutil import copyfile
import os


ATLAS_MRI_SUFFIX = 'brainsuite.icbm452.lpi.v08a.img'
ATLAS_LABEL_SUFFIX = 'brainsuite.icbm452.v15a.label.img'

BRAINSUITE_ATLAS_DIRECTORY = "/opt/BrainSuite17a/atlas/"


def runWorkflow(SUBJECT_ID, INPUT_MRI_FILE, WORKFLOW_BASE_DIRECTORY, BIDS_DIRECTORY, **keyword_parameters):
    layout = BIDSLayout(BIDS_DIRECTORY)

    WORKFLOW_NAME = SUBJECT_ID + "_cse"

    brainsuite_workflow = pe.Workflow(name=WORKFLOW_NAME)
    # brainsuite_workflow.base_dir = WORKFLOW_BASE_DIRECTORY
    brainsuite_workflow.base_dir = "/tmp"
    t1 = INPUT_MRI_FILE.split("/")[-1].replace("_T1w", '')
    copyfile(INPUT_MRI_FILE, os.path.join("/tmp", t1))

    bseObj = pe.Node(interface=bs.Bse(), name='BSE')
    bfcObj = pe.Node(interface=bs.Bfc(), name='BFC')
    pvcObj = pe.Node(interface=bs.Pvc(), name='PVC')
    cerebroObj = pe.Node(interface=bs.Cerebro(), name='CEREBRO')
    cortexObj = pe.Node(interface=bs.Cortex(), name='CORTEX')
    scrubmaskObj = pe.Node(interface=bs.Scrubmask(), name='SCRUBMASK')
    tcaObj = pe.Node(interface=bs.Tca(), name='TCA')
    dewispObj = pe.Node(interface=bs.Dewisp(), name='DEWISP')
    dfsObj = pe.Node(interface=bs.Dfs(), name='DFS')
    pialmeshObj = pe.Node(interface=bs.Pialmesh(), name='PIALMESH')
    hemisplitObj = pe.Node(interface=bs.Hemisplit(), name='HEMISPLIT')

    # =====Inputs=====

    # Provided input file
    bseObj.inputs.inputMRIFile = os.path.join("/tmp", t1)
    # Provided atlas files
    cerebroObj.inputs.inputAtlasMRIFile = (BRAINSUITE_ATLAS_DIRECTORY + ATLAS_MRI_SUFFIX)
    cerebroObj.inputs.inputAtlasLabelFile = (BRAINSUITE_ATLAS_DIRECTORY + ATLAS_LABEL_SUFFIX)

    # ====Parameters====
    bseObj.inputs.diffusionIterations = 3
    bseObj.inputs.diffusionConstant = 25  # -d
    bseObj.inputs.edgeDetectionConstant = 0.64  # -s
    bseObj.inputs.autoParameters = True

    # cerebroObj.inputs.useCentroids = False
    pialmeshObj.inputs.tissueThreshold = 1.05
    tcaObj.inputs.minCorrectionSize = 2500
    tcaObj.inputs.foregroundDelta = 20

    brainsuite_workflow.connect(bseObj, 'outputMRIVolume', bfcObj, 'inputMRIFile')
    brainsuite_workflow.connect(bfcObj, 'outputMRIVolume', pvcObj, 'inputMRIFile')
    brainsuite_workflow.connect(pvcObj, 'outputTissueFractionFile', cortexObj, 'inputTissueFractionFile')

    brainsuite_workflow.connect(bfcObj, 'outputMRIVolume', cerebroObj, 'inputMRIFile')
    brainsuite_workflow.connect(bseObj, 'outputMaskFile', cerebroObj, 'inputBrainMaskFile')
    brainsuite_workflow.connect(cerebroObj, 'outputLabelVolumeFile', cortexObj, 'inputHemisphereLabelFile')

    brainsuite_workflow.connect(cortexObj, 'outputCerebrumMask', scrubmaskObj, 'inputMaskFile')
    brainsuite_workflow.connect(scrubmaskObj, 'outputMaskFile', tcaObj, 'inputMaskFile')
    brainsuite_workflow.connect(tcaObj, 'outputMaskFile', dewispObj, 'inputMaskFile')
    brainsuite_workflow.connect(dewispObj, 'outputMaskFile', dfsObj, 'inputVolumeFile')
    brainsuite_workflow.connect(dfsObj, 'outputSurfaceFile', pialmeshObj, 'inputSurfaceFile')


    brainsuite_workflow.connect(pvcObj, 'outputTissueFractionFile', pialmeshObj, 'inputTissueFractionFile')
    brainsuite_workflow.connect(cerebroObj, 'outputCerebrumMaskFile', pialmeshObj, 'inputMaskFile')
    brainsuite_workflow.connect(pialmeshObj, 'outputSurfaceFile', hemisplitObj, 'pialSurfaceFile')


    brainsuite_workflow.connect(dfsObj, 'outputSurfaceFile', hemisplitObj, 'inputSurfaceFile')
    brainsuite_workflow.connect(cerebroObj, 'outputLabelVolumeFile', hemisplitObj, 'inputHemisphereLabelFile')

    ds = pe.Node(io.DataSink(), name='DATASINK')
    ds.inputs.base_directory = WORKFLOW_BASE_DIRECTORY

    # **DataSink connections**
    brainsuite_workflow.connect(bseObj, 'outputMRIVolume', ds, '@')
    brainsuite_workflow.connect(bseObj, 'outputMaskFile', ds, '@1')
    brainsuite_workflow.connect(bfcObj, 'outputMRIVolume', ds, '@2')
    brainsuite_workflow.connect(pvcObj, 'outputLabelFile', ds, '@3')
    brainsuite_workflow.connect(pvcObj, 'outputTissueFractionFile', ds, '@4')
    brainsuite_workflow.connect(cerebroObj, 'outputCerebrumMaskFile', ds, '@5')
    brainsuite_workflow.connect(cerebroObj, 'outputLabelVolumeFile', ds, '@6')
    brainsuite_workflow.connect(cerebroObj, 'outputAffineTransformFile', ds, '@7')
    brainsuite_workflow.connect(cerebroObj, 'outputWarpTransformFile', ds, '@8')
    brainsuite_workflow.connect(cortexObj, 'outputCerebrumMask', ds, '@9')
    brainsuite_workflow.connect(scrubmaskObj, 'outputMaskFile', ds, '@10')
    brainsuite_workflow.connect(tcaObj, 'outputMaskFile', ds, '@11')
    brainsuite_workflow.connect(dewispObj, 'outputMaskFile', ds, '@12')
    brainsuite_workflow.connect(dfsObj, 'outputSurfaceFile', ds, '@13')
    brainsuite_workflow.connect(pialmeshObj, 'outputSurfaceFile', ds, '@14')
    brainsuite_workflow.connect(hemisplitObj, 'outputLeftHemisphere', ds, '@15')
    brainsuite_workflow.connect(hemisplitObj, 'outputRightHemisphere', ds, '@16')
    brainsuite_workflow.connect(hemisplitObj, 'outputLeftPialHemisphere', ds, '@17')
    brainsuite_workflow.connect(hemisplitObj, 'outputRightPialHemisphere', ds, '@18')

    if 'BDP' in keyword_parameters:
        INPUT_DWI_BASE = keyword_parameters['BDP']
        bdpObj = pe.Node(interface=bs.BDP(), name='BDP')
        bdpInputBase = WORKFLOW_BASE_DIRECTORY + os.sep + SUBJECT_ID
                       # + '_T1w'

        # bdp inputs that will be created. We delay execution of BDP until all CSE and datasink are done
        bdpObj.inputs.bfcFile = bdpInputBase + '.bfc.nii.gz'
        bdpObj.inputs.inputDiffusionData = INPUT_DWI_BASE + '.nii.gz'
        dwiabspath = os.path.abspath(os.path.dirname(INPUT_DWI_BASE + '.nii.gz'))
        bdpObj.inputs.BVecBValPair = [keyword_parameters['BVEC'], keyword_parameters['BVAL']]

        bdpObj.inputs.estimateTensors = True
        bdpObj.inputs.estimateODF_FRACT = True
        bdpObj.inputs.estimateODF_FRT = True

        brainsuite_workflow.connect(ds, 'out_file', bdpObj, 'dataSinkDelay')

    if 'SVREG' in keyword_parameters:
        svregObj = pe.Node(interface=bs.SVReg(), name='SVREG')
        svregInputBase = WORKFLOW_BASE_DIRECTORY + os.sep + SUBJECT_ID
                         # + '_T1w'

        # svreg inputs that will be created. We delay execution of SVReg until all CSE and datasink are done
        svregObj.inputs.subjectFilePrefix = svregInputBase
        svregObj.inputs.atlasFilePrefix = '/opt/BrainSuite17a/svreg/BCI-DNI_brain_atlas/BCI-DNI_brain'
        if 'ATLAS' in keyword_parameters:
            svregObj.inputs.atlasFilePrefix = keyword_parameters['ATLAS']
        if 'SingleThread' in keyword_parameters:
            if 'ON' in keyword_parameters['SingleThread']:
                svregObj.inputs.useSingleThreading = True

        brainsuite_workflow.connect(ds, 'out_file', svregObj, 'dataSinkDelay')

        ds2 = pe.Node(io.DataSink(), name='DATASINK2')
        ds2.inputs.base_directory = WORKFLOW_BASE_DIRECTORY

        brainsuite_workflow.connect(svregObj, 'outputLabelFile', ds2, '@')

        thickPVCobj = pe.Node(bs.ThicknessPVC(), name='ThickPVC')
        thickPVCInputBase = WORKFLOW_BASE_DIRECTORY + os.sep + SUBJECT_ID
        thickPVCobj.inputs.subjectFilePrefix = thickPVCInputBase

        brainsuite_workflow.connect(ds2, 'out_file', thickPVCobj, 'dataSinkDelay')

    brainsuite_workflow.run(plugin='MultiProc', plugin_args={'n_procs': 2})



    # Print message when all processing is complete.
    print('Processing for subject %s has completed. Nipype workflow is located at: %s' % (
    SUBJECT_ID, WORKFLOW_BASE_DIRECTORY))
