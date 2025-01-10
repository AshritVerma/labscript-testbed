#####################################################################
#                                                                   #
# /example.py                                                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the program labscript, in the labscript      #
# suite (see http://labscriptsuite.org), and is licensed under the  #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

## 1/8: updated to use AOD-SLM alignment code output for updated AOD params from 

import time
import numpy as np
from scipy import signal
from labscript import (
    start,
    stop,
)
import labscriptlib.Rydberg.Subseqeuences_Utils.Sequence_Utils as utils
from labscriptlib.Rydberg.Subseqeuences_Utils.Subsequences import image_cmot, load_mot, compress_mot, reset_mot, zero_B_fields, zero_E_fields, reshape_dt, hold_dt, slm_set_zernike, image_dt, reshape_dt_3traps,reshape_dt_3traps_try2, setup_slm
from labscriptlib.Rydberg.Subseqeuences_Utils.Subsequences_singleatom import load_mot_singleatom, reset_mot_singleatom,hold_dt_singleatom,mloop_compress_mot_singleatom
from labscriptlib.Rydberg.Subseqeuences_Utils.MLOOP_Subsequences import mloop_hold_dt, mloop_compress_mot, mloop_reshape_dt
from labscriptlib.Rydberg.Rydberg_connection_table import cxn_table

if __name__ == '__main__':

    # Import and define the global variables for devices
    cxn_table()

    #### DEFINE PROBE, CONTROL DURATION:
    # probe_duration = SA_FLUORESCENCE_DURATION #2e-3 #100e-6 #5e-6 #15e-6#10e-6#5e-6#30e-6#300e-6 #30e-6 #100e-6#300e-6#300e-6 #50e-6 #150e-6
    probe_duration_second_image = MLOOP_PREPARATION_EIT_DURATION #SA_FLUORESCENCE_DURATION_NONDESTRUCTIVE
    probe_duration = probe_duration_second_image # added 3/21/2024
    control_duration = probe_duration #10e-6
    repeat_dead_time = 5e-6
    GATE_TIME = 10e-3 #10e-3 + SA_FLUORESCENCE_DURATION_NONDESTRUCTIVE #2e-3 #$10e-3 + SA_FLUORESCENCE_DURATION
    EXTRA_RESORTING_TIME = 50e-3
    cam_trigger_dur = probe_duration_second_image #5e-3 #$
    ##################################

    #### SETUP CAMERA PROPERTIES:

    # hamamatsu.camera_attributes['exposure'] = cam_trigger_dur #(probe_duration+ time_btw_prep_detect + preparation_duration + repeat_dead_time )*N_repeat+1e-3
    # hamamatsu.camera_attributes['subarrayMode'] = 2
    # hamamatsu.camera_attributes['subarrayHsize'] = HC_HSIZE
    # hamamatsu.camera_attributes['subarrayVsize'] = HC_VSIZE
    # hamamatsu.camera_attributes['subarrayHpos'] = HC_HPOS
    # hamamatsu.camera_attributes['subarrayVpos'] = HC_VPOS
    # # hamamatsu.camera_attributes['readoutMode'] = 1
    # ##################################


    resorting_parameters = {"Y_MIN_AOD_FREQ": Y_MIN_AOD + Y_OFFSET,
                    "Y_MAX_AOD_FREQ": Y_MAX_AOD + Y_OFFSET,
                    "X_MIN_AOD_FREQ": X_MIN_AOD + X_OFFSET,
                    "X_MAX_AOD_FREQ": X_MAX_AOD + X_OFFSET,
                    "Y_AOD_OFFSET": 0.0,
                    "X_AOD_OFFSET": 0.0,
                    "SWEEP_SPEED": SWEEP_SPEED,
                    "DWELL_TIME": DWELL_TIME,
                    "RISE_TIME": RISE_TIME,
                    "EARLY_PICK_UP_X": 0.0,
                    "LATE_DROP_OFF_X": 0.0,
                    "EARLY_PICK_UP_Y": 0.0,
                    "LATE_DROP_OFF_Y": 0.0,
                    "MAX_NUM_SWEEPS": 50,
                    "TARGET_CONFIG_FILE": 0,
                    "TARGET_CONFIG_FILE_NAME": "",  # Empty string
                    "TARGET_CONFIG_FILE_NUM_FRAMES": 1,
                    "PRIMARY_DIRECTION": 0,
                    "SIDE_TO_FILL": 0,
                    "NUM_LINES_TO_FILL": 1,
                    "NUM_TARGET_ROWS": 9,
                    "SORT_EXCESS_ATOMS": 1,
                    "NUM_COLS_TO_SORT": 9,
                    "COLS_TO_SORT_OFFSET": 0,
                    "VERTICAL_SORT": 0,
                    "PRE_SORT": 1,
                    "EJECT_EXCESS_ATOMS": EJECT_EXCESS_ATOMS,
                    "SKIP_EJECTION_ON_ALTERNATING_ITERATIONS": SKIP_EJECTION_ON_ALTERNATING_ITERATIONS,
                    "OPTIMIZE_SWEEPS": 1,
                    "STRIP_WAVEFORMS": 0,
                    "PARTIAL_MOVES": 0,
                    "TIMING_DIAGNOSTICS": 1
                    }


    # Camera_txt = {
    #     'roi': [1864, 2224, 1388, 1288],
    #     'exposure': 0.001,  
    #     'atom_size': 3,  
    #     'trap_locations': [[   1,  162,   32, 2300],
    #                     [   2,  204,   41, 2300],
    #                     [   3,  154,   76, 2300],
    #                     [   4,  196,   84, 2300]],
    #  }

    # Camera_txt = {
    #     'roi': [1864, 2224, 1388, 1288],
    #     'exposure': 0.001,  
    #     'atom_size': 3,  
    #     'trap_locations': [[   1,  162,   32, 2300],
    #                     [   2,  204,   41, 2300],
    #                     [   3,  158,   54, 2300],
    #                     [   4,  201,   62, 2300],
    #                     [   5,  154,   76, 2300],
    #                     [   6,  196,   84, 2300]],
    #  }

    # pixels = [(19, 151), (21, 159), (22, 167), (24, 176), (25, 184), (27, 149), (27, 193), (29, 158), (29, 202), (30, 210), (31, 167), (32, 174), (33, 219), (34, 183), (36, 147), (36, 192), (38, 156), (38, 200), (39, 209), (40, 165), (41, 173), (41, 217), (43, 181), (45, 190), (46, 198), (48, 207), (50, 216)]
    # thresholds = [247.0, 247.0, 248.0, 243.0, 251.0, 238.0, 252.0, 251.0, 249.0, 252.0, 249.0, 257.0, 249.0, 251.0, 242.0, 259.0, 243.0, 249.0, 248.0, 250.0, 248.0, 251.0, 251.0, 259.0, 246.0, 254.0, 245.0] 
    

    
    pixels =  [(19, 150), (21, 159), (22, 167), (23, 175), (25, 184), (27, 193), (29, 201), (30, 210), (33, 219), (28, 149), (29, 157), (31, 166), (32, 174), (35, 183), (36, 192), (38, 200), (39, 209), (41, 217), (36, 147), (37, 155), (40, 164), (41, 172), (43, 181), (45, 190), (46, 198), (48, 207), (50, 215)]
    thresholds = [233.0, 235.0, 235.0, 236.0, 241.0, 241.0, 241.0, 235.0, 235.0, 231.0, 238.0, 235.0, 238.0, 245.0, 250.0, 237.0, 235.0, 237.0, 228.0, 231.0, 233.0, 237.0, 236.0, 243.0, 235.0, 239.0, 237.0]

    pixels =  [(19, 150), (21, 159), (22, 167), (24, 175), (25, 184), (27, 193), (29, 201), (30, 209), (33, 219), (28, 149), (29, 157), (31, 166), (33, 174), (35, 183), (36, 191), (38, 200), (40, 208), (41, 217), (36, 147), (38, 155), (40, 164), (41, 172), (43, 181), (45, 190), (47, 198), (48, 207), (50, 215)] 
    thresholds = [226.0, 227.0, 225.0, 226.0, 231.0, 230.0, 231.0, 228.0, 228.0, 224.0, 230.0, 228.0, 236.0, 232.0, 232.0, 229.0, 232.0, 230.0, 220.0, 225.0, 228.0, 231.0, 228.0, 235.0, 226.0, 231.0, 230.0]
    thresolds = [233.0, 235.0, 235.0, 236.0, 241.0, 241.0, 241.0, 235.0, 235.0, 231.0, 238.0, 235.0, 238.0, 245.0, 250.0, 237.0, 235.0, 237.0, 228.0, 231.0, 233.0, 237.0, 236.0, 243.0, 235.0, 239.0, 237.0] 

    if len(pixels) != len(thresholds):
        raise ValueError("The length of pixels and thresholds must be the same.")
    
    # divide thresholds by conversion factor = 0.11 to convert electrons to photon counts
    CF = 0.11

    trap_locations = []
    for i in range(len(pixels)):
        trap_locations.append([i+1, pixels[i][1], pixels[i][0], thresholds[i]/CF])
    print(trap_locations)

    Camera_txt = {
        'roi': [HC_HPOS, HC_HPOS+HC_HSIZE, HC_VPOS+HC_VSIZE, HC_VPOS],
        'exposure': 0.001,  
        'atom_size': 3,  
        'trap_locations': trap_locations
        # 'trap_locations': [[   1,  166,   10, 2300],
        #                 [   2,  209,   19, 2300],
        #                 [   3,  162,   32, 2300],
        #                 [   4,  205,   40, 2300],
        #                 [   5,  158,   54, 2300],
        #                 [   6,  201,   63, 2300]],
        # 'trap_locations': [[   1,  166,   10, 2160],
        #                 [   2,  209,   19, 2160],
        #                 [   3,  162,   32, 2160],
        #                 [   4,  205,   41, 2160],
        #                 [   5,  158,   54, 2160],
        #                 [   6,  201,   63, 2160]],    
        # 'trap_locations': [[   1,  165,   8, 2136],
        #                 [   2,  208,   16, 2218],
        #                 [   3,  162,   30, 2155],
        #                 [   4,  204,   38, 2200],
        #                 [   5,  158,   51, 2155],
        #                 [   6,  200,   60, 2200]],    
    }
    # [(8, 165), (16, 208), (30, 161), (38, 204), (52, 158), (60, 200)]
    #  [(32, 162), (41, 204), (54, 158), (62, 201), (76, 154), (84, 196)]
    # [(10, 166), (19, 209), (32, 162), (40, 205), (54, 158), (63, 201)]


    hamamatsu.change_resorting_txt(resorting_parameters)
    hamamatsu.change_camera_config_txt(Camera_txt)




    ### SETUP LASER FREQUENCY OF PREPARATION, SACHER AND CONTROL:
    # pts_probe.program_single_freq(SA_FLUORESCENCE_FREQ_LOSS)#SA_FLUORESCENCE_FREQ)#PROBE_FREQ)#(1145)
    # pts_probe.program_single_freq(MLOOP_EIT_COOLING_LASER_FREQ)#SA_FLUORESCENCE_FREQ)#PROBE_FREQ)#(1145)
    pts_probe.program_single_freq(MLOOP_PREPARATION_EIT_LASER_FREQ)#SA_FLUORESCENCE_FREQ)#PROBE_FREQ)#(1145)
    
    # #### for polarized repump on-resonance with 1->2
    # ACSS = (1400-1384)*1.4
    # STARK_SHIFTED_2_2_TRANSITION = 1400 - ACSS
    # srs384.set_freq_amp(3.417*10**9 - (STARK_SHIFTED_2_2_TRANSITION - MLOOP_PREPARATION_EIT_LASER_FREQ)/2*10**6, 16) # for polarized repump
    # # srs384.set_freq_amp(3.417*10**9 - (1400 - (1400-1384)*1.4 - MLOOP_EIT_COOLING_LASER_FREQ)/2*10**6, 16) # for polarized repump
    # # srs384.set_freq_amp(3.02*10**9, 16)

    #### polarized repump on sacher
    #### for BLUE-DETUNED polarized repump
    srs384.set_freq_amp(3.417*10**9 + MLOOP_PREPARATION_EIT_SACHER_REPUMP_DET/2*10**6, 16) # for polarized repump
    # srs384.set_freq_amp(3.417*10**9 - (1400 - (1400-1384)*1.4 - MLOOP_EIT_COOLING_LASER_FREQ)/2*10**6, 16) # for polarized repump
    # srs384.set_freq_amp(3.02*10**9, 16)

    ##### heatload
    hp_sg1.set_freq_amp(MLOOP_PREPARATION_EIT_HEATING_FREQ + (MLOOP_PREPARATION_HEATLOAD_REPUMP_FREQUENCY-5573e6)/1e6, MLOOP_PREPARATION_HEATLOAD_SIDEBAND_POWER)#D2_EIT_HEATING_FREQ, -20)
    # hp_sg1.set_freq_amp(MLOOP_PREPARATION_EIT_HEATING_FREQ + (MLOOP_PREPARATION_HEATLOAD_REPUMP_FREQUENCY-5573e6)/1e6, -20)#D2_EIT_HEATING_FREQ, -20)
    # print(MLOOP_PREPARATION_EIT_HEATING_FREQ + (MLOOP_PREPARATION_HEATLOAD_REPUMP_FREQUENCY-5573e6)/1e6)
    # print(MLOOP_PREPARATION_HEATLOAD_REPUMP_FREQUENCY)

    ########### 795 repump frequency:
    ## SATISFY GREY MOLASSES RESONANCE (2 photon)
    # srs384.set_freq_amp(SA_MLOOP_D1_REPUMP_FREQ00, SA_MLOOP_D1_REPUMP_POW00)#OP_795_EOM_FREQ,4) # for 795 OP
    agilent_sg1.set_freq_amp(SA_D1_EOM_PDH*10**6,0) # assuming preparation frequency is in MHz

    ##################################
    d2_eit_half_waveplate.constant(MLOOP_EIT_COOLING_HWP, units='deg')

    # # Parametric heating:
    # agilent_awg1.program_gated_sine(SA_PARAMETRIC_HEATING_FREQ, SA_PARAMETRIC_HEATING_AMPL, SA_PARAMETRIC_HEATING_OFFSET)

    # Chis's mirrors:
    # mirror_controller.set_position("spcm_close", 10295, 35488) # example

    ### SETUP SLM:
    setup_slm(same_defocus = True) # added july 19th
    # setup_slm()
    ##################################



    t=0
    start()

    # # For parametric heating:
    # agilent_awg1.trigger(t, duration=0.3764)#5e-3+DT_WAIT_DURATION+50e-3+23e-3+1)

    # spectrum_awg_808AOD.add_segment(.001, {0: string_x10_808AOD, 1:string_x1_808AOD}, N_samples_808AOD)

    
    #############################################################################################################
    #############################################################################################################
    print('-------------Running Experiments (Dec 2023 version labscript)------------')
    def normalize_inten(li):
        total=sum(li)
        return list(np.array(li)/total/1.03)
    
    def calculate_phase_from_article(An_li):
        N=len(An_li)
        ans=[0]
        for i in range(2,N+1):
            temp=ans[0]
            for j in range(1,i):
                temp-=2*np.pi*(i-j)*An_li[j-1]
            ans.append(temp)
        return ans
    
    nx_traps = 9
    ny_traps = 3

    ########### center X is at 100.575
    ########### center Y is at 95.75

    # # calibrated
    # freq_x_spacing = 7.95/50*10 # per 10.1um
    # freq_y_spacing = 8.2/50*10 # per 10.1um

    # # 3x9, after optimizing the AOD frequencies
    # xmin = 94.215+0.07 -0.10
    # ymin = 94.11 + 0.05
    # freqs_x =  list(xmin + np.arange(nx_traps)*freq_x_spacing - 90)
    # freqs_y = list(ymin + np.arange(ny_traps)*freq_y_spacing - 89)

    # print('XMIN: %g' %(np.min(freqs_x)+90))
    # print('XMAX: %g' %(np.max(freqs_x)+90))
    # print('YMIN: %g' %(np.min(freqs_y)+89))
    # print('YMAX: %g' %(np.max(freqs_y)+89))


    # freqs_x = [10+2*i - nx_traps/2 for i in range(nx_traps)]
    # freqs_y = [10+2*i - ny_traps/2 for i in range(ny_traps)]#, 12]

    # # 2x2    
    # freqs_x =  list(np.array([97, 105])-90 -0.1)#[8+2*i - nx_traps/2 for i in range(nx_traps)]
    # freqs_y = list(np.array([95.8+0.1, 104])-89 -0.15) #[98.25-89, 99.85-89, 101.5-89]
    
    # # 2x3, after optimizing the AOD frequencies
    # freqs_x =  list(np.array([96.6, 104.55])-90)#[8+2*i - nx_traps/2 for i in range(nx_traps)]
    # # freqs_x =  list(np.array([96.6, 104.8])-90)#[8+2*i - nx_traps/2 for i in range(nx_traps)]
    # freqs_y = list(np.array([ 95.75, 99.85, 103.95])-89 - 4.1) #[98.25-89, 99.85-89, 101.5-89]
    # # freqs_x =  list(np.array([96.6, 104.55])-90)#[8+2*i - nx_traps/2 for i in range(nx_traps)]
    # # freqs_y = list(np.array([ 95.75])-89) #[98.25-89, 99.85-89, 101.5-89]

    # use low power

    
    nx_traps = NUM_COL
    ny_traps = NUM_ROW
    freqs_x = list(np.linspace(X_MAX_AOD+X_OFFSET,X_MIN_AOD+X_OFFSET,9)-90)
    freqs_y = list(np.linspace(Y_MIN_AOD+Y_OFFSET,Y_MAX_AOD+Y_OFFSET,3)-89)

    Inten_x = [10/nx_traps/10]*nx_traps
    Inten_y = [20/ny_traps/10]*ny_traps

    phases_x = calculate_phase_from_article(Inten_x)
    # phases_x = [4.75227278, 0.70198217, 4.65791282, 3.12949299, 5.11857056, 0.8296182, 0.65181831, 0.15400336, 1.31281738, 0.24798014][:nx_traps]
    phases_y = calculate_phase_from_article(Inten_y)
    print(phases_x)
    # phases_y = [4.75227278, 0.70198217, 4.65791282, 3.12949299, 5.11857056, 0.8296182, 0.65181831, 0.15400336, 1.31281738, 0.24798014][:ny_traps]
    
    print('phases_x',phases_x)
    print('phases_y',phases_y)
    
    init_inten = Inten_x #[0] #Inten_x
    init_inten_y = Inten_y #[0,0,0] #Inten_y
    
    fin_inten = Inten_x # Inten_x #[10/nx_traps]*snx_traps
    fin_inten_y = Inten_y # Inten_y #[20/ny_traps]*nx_traps

    moved_freq_x =  freqs_x # list(np.array([102.067-90]) - 0.55 - 1.585*2 - 1)#[8+2*i - nx_traps/2 for i in range(nx_traps)]
    moved_freq_y = freqs_y # list(np.array([100.25-89, 101.9018-89, 101.9018-89 + 1.65]) - 0.4 - 1.65)

    Move_time = SA_SINGLE_MOVE_TIME #50 # units us

    spectrum_awg_808AOD.add_phase(phases_x, phases_y)
    spectrum_awg_808AOD.def_freqs(freqs_x, freqs_y)
    spectrum_awg_808AOD.def_intens(init_inten, fin_inten, init_inten_y, fin_inten_y)
    spectrum_awg_808AOD.def_moved_freqs(moved_freq_x, moved_freq_y, Move_time)
    
    if not RESORT_ROYGLAUBER:
        spectrum_card_royal.enable(t)
        # spectrum_awg_808AOD.reset(t)
        # t+=50e-6
        spectrum_awg_808AOD.reset(t)
        t+=30e-3



    #############################################################################################################
    #############################################################################################################


    t+=0.003
    laser_freq_jumping_box_ad9959.jump_frequency(t, "Prep", SA_FLUORESCENCE_FREQ*1e6, trigger=False)#SA_MOLASSES_FREQ*1e6, trigger=False)
    laser_freq_jumping_box_ad9959.jump_frequency(t, "D1det", (SA_MLOOP_D1_FLUORESCENCE_FREQ00)*1e6, trigger=False)#SA_MOLASSES_FREQ*1e6, trigger=False)

    # spectrum_awg_808AOD.add_segment(t, {0: string_x10_808AOD, 1:string_x1_808AOD}, N_samples_808AOD)

    #####################################################################################
    ### MOT LOADING AND DT TRAPPING STAGE
    t += load_mot_singleatom(t,0.1)#1)#load_mot(t, 1)
    t += mloop_compress_mot(t, 40e-3)
    # t += mloop_compress_mot_singleatom(t,40e-3) #

    mot_shutter.disable(t) # close MOT shutter #$
    zero_B_fields(t, Fluorescence_SA = True, duration = 5e-3) # zero-ing small Z coil
    utils.jump_from_previous_value(z_coil, t, 0.0) # big Z coil
    t+= 1e-3#0.001
    
    t += hold_dt_singleatom(t, duration=SA_DT_WAIT_DURATION) #hold_dt(t, duration=SA_DT_WAIT_DURATION)
    #####################################################################################

    #####################################################################################
    ### B FIELD RAMPING AND OPTICAL PUMPING STAGE
    #add_time_marker(t, "RAMP_UP_B_FIELD")
    # # For fluorescence imaging don't do high Bz:
    utils.jump_from_previous_value(z_coil, t, 0.0)

    # # For fluorescence imaging don't do high Bz:
    # utils.jump_from_previous_value(x_coil, t, 10.0)
    # utils.jump_from_previous_value(y_coil, t, 4.1)
    t+= 2e-3
    #####################################################################################

    # Put atoms in F=2 before optical pumping
    utils.jump_from_previous_value(repump_aom_power, t, 2)
    repump_aom_switch.enable(t)
    t+= 300e-6
    repump_aom_switch.disable(t)
    utils.jump_from_previous_value(repump_aom_power, t, 0)



    ## For MOT fluorescence keep repump shutter open:
    # repump_shutter.disable(t) # close repump shutter

    ### FOR FLUORESCENCE: If we use MOT for fluorescence imaging:
    # mot_shutter.enable(t) # mot shutter needs to be high to open the shutter
    # top_mot_shutter.disable(t) # turn off top mot shutter because of scattering
    motl_repump_ad9959.jump_frequency(t, "MOT", SA_FLUORESCENCE_MOTL_FREQ, trigger=True)#trigger=False)
    
    ### ADD THIS TO TEST IF HAMAMATSU GETS SOME CRAP FROM MOT FLUORESCENCE EVEN THOUGH IT SHOULD NOT..
    hamamatsu.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)#50e-6)
    # hamamatsu_glauber.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)#50e-6)
    t+=GATE_TIME

    # ####################################################################################
    # #### MOLASSES SEQUENCE:
    # utils.jump_from_previous_value(fluorescence_aom_power, t, SA_MOLASSES_POWER)
    # fluorescence_aom_switch.enable(t + 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, SA_MOLASSES_REPUMP_POWER)#2)
    # repump_aom_switch.enable(t+ 1.5e-6)
    # t += SA_MOLASSES_DURATION#50e-6
    # utils.jump_from_previous_value(fluorescence_aom_power, t, 0.0)
    # fluorescence_aom_switch.disable(t + 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, 0)
    # repump_aom_switch.disable(t+ 1.5e-6)
    # # mot_shutter.disable(t) ## Somehow having this here doesn't really work..?
    # t += repeat_dead_time 
    # ################################################################

    ################################################################ FOR ZEROING OF THE B FIELD
    # utils.jump_from_previous_value(fluorescence_aom_power, t, SA_FLUORESCENCE_POWER)
    # fluorescence_aom_switch.enable(t + 1.5e-6)
    # # ### if we use MOT light for imaging
    # # utils.jump_from_previous_value(motl_aom_power, t, FLUORESCENCE_MOT_POWER_TEST)
    # # motl_aom_switch.enable(t + 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, SA_FLUORESCENCE_REPUMP_POWER)#2)
    # repump_aom_switch.enable(t+ 1.5e-6)
    # t += 200e-3#50e-6
    # utils.jump_from_previous_value(fluorescence_aom_power, t, 0.0)
    # fluorescence_aom_switch.disable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # utils.jump_from_previous_value(motl_aom_power, t, 0.0)
    # motl_aom_switch.disable(t+ 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, 0)
    # repump_aom_switch.disable(t+ 1.5e-6)
    # ################################################################

    ############################################################### RAMP UP THE SIDE TRAP
    # # # ramp up the side trap
    # utils.jump_from_previous_value(dt785_aom_power, t, 0)#1)#0.7)#2)
    # t += 10e-6
    # dt785_aom_switch.enable(t) ###### WITH AWG, TRAP SUDDENLY TURNS ON -> CAN CAUSE SIGNIFICANT LOSSES!!!!!!
    # utils.ramp_from_previous_value(dt785_aom_power, t, duration=10e-3, final_value=MOT_DT785_POWER, samplerate=COIL_SAMPLE_RATE)
    # t += 10e-3 #15e-3#10e-3

    # # measure heating rate/lifetime
    # t += 100e-3#TEST_DURATION
    # For parametric heating:
    # agilent_awg1.trigger(t, duration=0.03)#5e-3+DT_WAIT_DURATION+50e-3+23e-3+1)

    # # # # longer 
    # agilent_awg1.trigger(t, duration=0.1)#5e-3+DT_WAIT_DURATION+50e-3+23e-3+1)
    # t+=100e-3


    # # # ramp down the side trap
    # tisaph_aom_switch.disable(t+10e-3) ###### WITH AWG, TRAP SUDDENLY TURNS OFF -> CAN CAUSE SIGNIFICANT LOSSES!!!!!!
    # utils.ramp_from_previous_value(tisaph_aom_power, t, duration=10e-3, final_value=0, samplerate=COIL_SAMPLE_RATE)
    # t += 15e-3
    
    #  # # # #####################################################################################
    # #### Ramp down the top trap
    # t += 10e-6
    # utils.ramp_from_previous_value(dt808_aom_power, t, duration=10e-3, final_value=SA_MOT_DT808_POWER_FINAL, samplerate=COIL_SAMPLE_RATE)
    # t+= 15e-3
    # ###############################################################

    t += 1e-3 #20e-3 #60e-3 #1e-3?
    laser_freq_jumping_box_ad9959.jump_frequency(t, "Prep", SA_FLUORESCENCE_FREQ*1e6, trigger=True)

    t += 1e-3 #20e-3 #60e-3 #1e-3?
    # #####################################################################################

    ############################### MOLASSES ################################
    utils.jump_from_previous_value(fluorescence_aom_power, t, SA_FLUORESCENCE_POWER)#SA_FLUORESCENCE_POWER_SEC)
    fluorescence_aom_switch.enable(t + 1.5e-6)
    ### if we use MOT light for imaging
    # utils.jump_from_previous_value(motl_aom_power, t, FLUORESCENCE_MOT_POWER_TEST)
    # motl_aom_switch.enable(t + 1.5e-6)
    utils.jump_from_previous_value(repump_aom_power, t, SA_FLUORESCENCE_REPUMP_POWER)#SA_FLUORESCENCE_REPUMP_POWER_SEC)#2)
    repump_aom_switch.enable(t+ 1.5e-6)
    t += 10e-3#50e-6
    utils.jump_from_previous_value(fluorescence_aom_power, t, 0.0)
    fluorescence_aom_switch.disable(t + 1.5e-6)
    ### if we use MOT light for imaging
    utils.jump_from_previous_value(motl_aom_power, t, 0.0)
    motl_aom_switch.disable(t+ 1.5e-6)
    utils.jump_from_previous_value(repump_aom_power, t, 0)
    repump_aom_switch.disable(t+ 1.5e-6)
    # ############################### END OF MOLASSES ################################
    t+= 80e-3
    
    #####################################################################################
    ### FIRST ATOM IMAGE
    hamamatsu.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)#50e-6)
    # hamamatsu_glauber.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)#50e-6)


    utils.jump_from_previous_value(fluorescence_aom_power, t, SA_FLUORESCENCE_POWER)
    fluorescence_aom_switch.enable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # utils.jump_from_previous_value(motl_aom_power, t, FLUORESCENCE_MOT_POWER_TEST)
    # motl_aom_switch.enable(t + 1.5e-6)
    utils.jump_from_previous_value(repump_aom_power, t, SA_FLUORESCENCE_REPUMP_POWER)#2)
    repump_aom_switch.enable(t+ 1.5e-6)
    t += probe_duration#50e-6
    utils.jump_from_previous_value(fluorescence_aom_power, t, 0.0)
    fluorescence_aom_switch.disable(t + 1.5e-6)
    ### if we use MOT light for imaging
    utils.jump_from_previous_value(motl_aom_power, t, 0.0)
    motl_aom_switch.disable(t+ 1.5e-6)
    utils.jump_from_previous_value(repump_aom_power, t, 0)
    repump_aom_switch.disable(t+ 1.5e-6)
    # mot_shutter.disable(t) ## Somehow having this here doesn't really work..?
    t += repeat_dead_time 

    #####################################################################################
    # t+= TEST_DURATION

    # # #################################################################
    # # FIND STARK SHIFT
    # t+= 100e-6
    # # DEPUMP FREQUENCY
    # laser_freq_jumping_box_ad9959.jump_frequency(t, "D1det", SA_D1_RES_FREQ*1e6, trigger=True)#SA_MOLASSES_FREQ*1e6, trigger=False)
    # # PUSHOUT FREQUENCY
    # laser_freq_jumping_box_ad9959.jump_frequency(t, "Prep", SA_D2_RES_FREQ*1e6, trigger=True)#SA_MOLASSES_FREQ*1e6, trigger=False)
    # # laser_freq_jumping_box_ad9959.jump_frequency(t, "Prep", 1396*1e6, trigger=True)
    # t += 1e-3 #20e-3 #60e-3 #1e-3?
    
    # # put atoms in F = 2
    # utils.jump_from_previous_value(repump_aom_power, t, 2)
    # repump_aom_switch.enable(t)
    # t += 1e-3
    # repump_aom_switch.disable(t)
    # utils.jump_from_previous_value(repump_aom_power, t, 0)
    # t += 10e-6

    # # # depump atoms into F = 1
    # # dt808_aom_switch.disable(t)
    # utils.jump_from_previous_value(D1_aom_power, t, 0.5)#1)#0.5)#1)
    # D1_aom_switch.enable(t)
    # t += 5e-6
    # utils.jump_from_previous_value(D1_aom_power, t, 0.0)
    # D1_aom_switch.disable(t)
    # # dt808_aom_switch.enable(t)
    # t += 10e-6

    # # resonant pushout on 2->3
    # utils.jump_from_previous_value(fluorescence_aom_power, t, 2)
    # fluorescence_aom_switch.enable(t)
    # t+= 10e-3
    # fluorescence_aom_switch.disable(t)
    # utils.jump_from_previous_value(fluorescence_aom_power, t, 0)
    # t+= 10e-6

    # t += 1e-3 #20e-3 #60e-3 #1e-3?
    # laser_freq_jumping_box_ad9959.jump_frequency(t, "Prep", SA_FLUORESCENCE_FREQ*1e6, trigger=True)
    # # #################################################################

    # #####################################################################################
    utils.jump_from_previous_value(x_coil, t, D2_EIT_COOLING_B_FIELD_X)
    # laser_freq_jumping_box_ad9959.jump_frequency(t, "D1det", (MLOOP_EIT_COOLING_PI_AOM_FREQ00)*32*1e6, trigger=False) # for first step
    ################################ top_mot_shutter.disable(t) # turn off top mot shutter because of retro for D2 EIT
    top_mot_shutter.disable(t)
    t += 10e-6
    ##### Ramp up the side trap
    # utils.jump_from_previous_value(tisaph_aom_power, t, 0)#1)#0.7)#2)
    # t += 10e-6
    # tisaph_aom_switch.enable(t)
    # utils.ramp_from_previous_value(tisaph_aom_power, t, duration=10e-3, final_value=SA_MOT_TISAPH_POWER, samplerate=COIL_SAMPLE_RATE)
    
    # # #### Ramp the top trap
    # utils.ramp_from_previous_value(dt808_aom_power, t, duration=10e-3, final_value=SA_MOT_DT808_POWER_FINAL, samplerate=COIL_SAMPLE_RATE)
    
    ######## SWITCH THE B FIELDS
    fluorescence_shutter.disable(t)
    # zero_B_fields(t, Fluorescence_Bx = True, duration = 5e-3) 
    # t += 11e-3
    utils.jump_from_previous_value(y_coil, t, -2)#0.3)#2)
    utils.jump_from_previous_value(small_z_coil, t, -2)#0.3)#2)
    t+= 2e-3
    zero_B_fields(t, Fluorescence_Bx = True, duration = 5e-3) 

    # repump frequency for EIT preparation
    motl_repump_ad9959.jump_frequency(t, "Repump", MLOOP_PREPARATION_HEATLOAD_REPUMP_FREQUENCY, trigger=True)#trigger=False)

    t += 21e-3
    ########################################################################


    #####################################################################################
    ### SECOND ATOM IMAGE   
    ### WE HAVE 21ms ABOVE 
    # t += GATE_TIME # add time between different kinetic shots
    # t += 100e-3 # add time between different kinetic shots
    hamamatsu.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)# trigger_duration = ((probe_duration + repeat_dead_time )*N_repeat+1e-3))#50e-6)
    # hamamatsu_glauber.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)# trigger_duration = ((probe_duration + repeat_dead_time )*N_repeat+1e-3))#50e-6)

    ##################################### PGC IMAGING
    # utils.jump_from_previous_value(fluorescence_aom_power, t, SA_FLUORESCENCE_POWER)#SA_FLUORESCENCE_POWER_SEC)
    # fluorescence_aom_switch.enable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # # utils.jump_from_previous_value(motl_aom_power, t, FLUORESCENCE_MOT_POWER_TEST)
    # # motl_aom_switch.enable(t + 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, SA_FLUORESCENCE_REPUMP_POWER)#SA_FLUORESCENCE_REPUMP_POWER_SEC)#2)
    # repump_aom_switch.enable(t+ 1.5e-6)
    # t += probe_duration_second_image#50e-6
    # utils.jump_from_previous_value(fluorescence_aom_power, t, 0.0)
    # fluorescence_aom_switch.disable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # utils.jump_from_previous_value(motl_aom_power, t, 0.0)
    # motl_aom_switch.disable(t+ 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, 0)
    # repump_aom_switch.disable(t+ 1.5e-6)
    # # mot_shutter.disable(t) ## Somehow having this here doesn't really work..?
    # t += repeat_dead_time 
    # # t += TEST_DURATION
    #####################################################################################

    ################ D2 EIT IMAGING ################
    num_points = 1#MLOOP_EIT_COOLING_NUM_POINTS
    total_cooling_duration = 0

    D2_next_pi_AOM = eval("MLOOP_PREPARATION_EIT_PI_FREQ")
    laser_freq_jumping_box_ad9959.jump_frequency(t, "D1det", (D2_next_pi_AOM)*32*1e6, trigger=True)#SA_MOLASSES_FREQ*1e6, trigger=False)  

    t+=1e-3
    
    if D2_EIT_HEATING_SWITCH:
        utils.jump_from_previous_value(op_aom_power, t, MLOOP_PREPARATION_EIT_HEATING_POWER)#1)#0.7)#2)
        op_aom_switch.enable(t)
    sigma_pow = eval("MLOOP_PREPARATION_EIT_SIGMA_POWER")
    utils.jump_from_previous_value(sacher_aom_power, t, sigma_pow)#1)#0.7)#2)
    sacher_aom_switch.enable(t)
    pi_pow = eval("MLOOP_PREPARATION_EIT_PI_POWER")
    utils.jump_from_previous_value(D1_aom_power, t, pi_pow)
    D1_aom_switch.enable(t)
    
    D2_imaging_dur = eval("MLOOP_PREPARATION_EIT_DURATION")

    t += D2_imaging_dur
    utils.jump_from_previous_value(D1_aom_power, t, 0.0)
    D1_aom_switch.disable(t)
    utils.jump_from_previous_value(sacher_aom_power, t, 0.0)
    sacher_aom_switch.disable(t)
    utils.jump_from_previous_value(op_aom_power, t, 0)#1)#0.7)#2)
    op_aom_switch.disable(t)
    
    t+= 20e-6
    # time_difference = D2_EIT_HEATING_DURATION - total_cooling_duration
    # if time_difference >0:
    #     t+= time_difference
    ################

    # ############### PARAMETRIC HEATING ########################################
    # # # # ramp up the side trap
    # # utils.jump_from_previous_value(tisaph_aom_power, t, 0)#1)#0.7)#2)
    # # t += 10e-6
    # # tisaph_aom_switch.enable(t) ###### WITH AWG, TRAP SUDDENLY TURNS ON -> CAN CAUSE SIGNIFICANT LOSSES!!!!!!
    # # utils.ramp_from_previous_value(tisaph_aom_power, t, duration=10e-3, final_value=SA_MOT_TISAPH_POWER, samplerate=COIL_SAMPLE_RATE)
    # # t += 10e-3 #15e-3#10e-3

    # # # measure heating rate/lifetime
    # # t += 100e-3#TEST_DURATION
    # # For parametric heating:
    # # agilent_awg1.trigger(t, duration=0.03)#5e-3+DT_WAIT_DURATION+50e-3+23e-3+1)

    # # # # longer 
    # agilent_awg1.trigger(t, duration=0.05)#5e-3+DT_WAIT_DURATION+50e-3+23e-3+1)
    # t+=100e-3

    # # # # ramp down the side trap
    # # tisaph_aom_switch.disable(t+10e-3) ###### WITH AWG, TRAP SUDDENLY TURNS OFF -> CAN CAUSE SIGNIFICANT LOSSES!!!!!!
    # # utils.ramp_from_previous_value(tisaph_aom_power, t, duration=10e-3, final_value=0, samplerate=COIL_SAMPLE_RATE)
    # # t += 15e-3

    # ############# RELEASE AND RECAPTURE #########################################
    # t+= 20e-6
    # dt808_aom_switch.disable(t)
    # t += D2_EIT_COOLING_TURNOFF_TRAP_DURATION
    # dt808_aom_switch.enable(t)
    # #######################################################################################
    # top_mot_shutter.enable(t) # turn on top mot shutter for fluorescence
    # t += 10e-3
    # # # #####################################################################################

    # # # # #####################################################################################
    # #### Ramp down the top trap
    # t += 10e-6
    # utils.ramp_from_previous_value(dt808_aom_power, t, duration=10e-3, final_value=SA_MOT_DT808_POWER_FINAL, samplerate=COIL_SAMPLE_RATE)
    # t+= 15e-3
    
    # # ramp up the top trap
    # utils.ramp_from_previous_value(dt808_aom_power, t, duration=10e-3, final_value=SA_MOT_DT808_POWER, samplerate=COIL_SAMPLE_RATE)
    # # zero_B_fields(t, Fluorescence_SA = True, duration = 5e-3)
    # t += 10e-3
    # # # # #####################################################################################


    #####################################################################################
    ##### MEASURE AC STARK SHIFT

    # Put atoms in F=2 before optical pumping
    # utils.jump_from_previous_value(repump_aom_power, t, 2)
    # repump_aom_switch.enable(t)
    # dt808_aom_switch.disable(t)

    # # 2V = 830uW after dichroic
    # # 0.7V = 230uW
    # # 1V = 350uW
    # utils.jump_from_previous_value(sacher_aom_power, t, 2)#1)#0.7)#2)
    # sacher_aom_switch.enable(t + 1.5e-6)
    # t += SA_LOSS_DURATION#50e-6
    # utils.jump_from_previous_value(sacher_aom_power, t, 0.0)
    # sacher_aom_switch.disable(t + 1.5e-6)

    # repump_aom_switch.disable(t)
    # utils.jump_from_previous_value(repump_aom_power, t, 0)
    # dt808_aom_switch.enable(t)
    # t+=5e-3
    ##### END OF MEASURE AC STARK SHIFT
    #####################################################################################


    # #############################################################################################
    ### Atom movement
    
    # t += 10e-3 # add time between different kinetic shots
    # spectrum_awg_808AOD.reset(t)
    # t+=50e-6
    # spectrum_awg_808AOD.reset(t)
    # t+=50e-6
    # # spectrum_awg_808AOD.reset(t)
    # # t+=10e-3

    # spectrum_awg_808AOD.reset(t)
    # t+=150e-6
    # spectrum_awg_808AOD.reset(t)
    # t+=10e-3
    # #############################################################################################



    #####################################################################################
    ### THIRD ATOM IMAGE   
    t += GATE_TIME # add time between different kinetic shots
    t += EXTRA_RESORTING_TIME
    # t += GATE_TIME # add time between different kinetic shots

    # spectrum_awg_808AOD.reset(t)
    # t+=50e-6
    # spectrum_awg_808AOD.reset(t)
    # t+=3e-3

    # # ############# RELEASE AND RECAPTURE #########################################
    # gap_time = 1e-3 # time between trap turning back on and exposure time
    # tisaph2_aom_switch.disable(t-gap_time - TURNOFF_TRAP_DURATION)
    # tisaph2_aom_switch.enable(t-gap_time)
    # # #############################################################################################

    # t += 100e-3
    hamamatsu.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)# trigger_duration = ((probe_duration + repeat_dead_time )*N_repeat+1e-3))#50e-6)
    # hamamatsu_glauber.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)# trigger_duration = ((probe_duration + repeat_dead_time )*N_repeat+1e-3))#50e-6)


    # ######################################
    # utils.jump_from_previous_value(fluorescence_aom_power, t, SA_FLUORESCENCE_POWER)#SA_FLUORESCENCE_POWER_SEC)
    # fluorescence_aom_switch.enable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # # utils.jump_from_previous_value(motl_aom_power, t, FLUORESCENCE_MOT_POWER_TEST)
    # # motl_aom_switch.enable(t + 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, SA_FLUORESCENCE_REPUMP_POWER)#SA_FLUORESCENCE_REPUMP_POWER_SEC)#2)
    # repump_aom_switch.enable(t+ 1.5e-6)
    # t += probe_duration_second_image#50e-6
    # utils.jump_from_previous_value(fluorescence_aom_power, t, 0.0)
    # fluorescence_aom_switch.disable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # utils.jump_from_previous_value(motl_aom_power, t, 0.0)
    # motl_aom_switch.disable(t+ 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, 0)
    # repump_aom_switch.disable(t+ 1.5e-6)
    # # mot_shutter.disable(t) ## Somehow having this here doesn't really work..?
    # t += repeat_dead_time 
    # ######################################


    ################ D2 EIT IMAGING ################
    num_points = 1#MLOOP_EIT_COOLING_NUM_POINTS
    total_cooling_duration = 0

    D2_next_pi_AOM = eval("MLOOP_PREPARATION_EIT_PI_FREQ")
    laser_freq_jumping_box_ad9959.jump_frequency(t, "D1det", (D2_next_pi_AOM)*32*1e6, trigger=True)#SA_MOLASSES_FREQ*1e6, trigger=False)  

    t+=1e-3
    
    if D2_EIT_HEATING_SWITCH:
        utils.jump_from_previous_value(op_aom_power, t, MLOOP_PREPARATION_EIT_HEATING_POWER)#1)#0.7)#2)
        op_aom_switch.enable(t)
    sigma_pow = eval("MLOOP_PREPARATION_EIT_SIGMA_POWER")
    utils.jump_from_previous_value(sacher_aom_power, t, sigma_pow)#1)#0.7)#2)
    sacher_aom_switch.enable(t)
    pi_pow = eval("MLOOP_PREPARATION_EIT_PI_POWER")
    utils.jump_from_previous_value(D1_aom_power, t, pi_pow)
    D1_aom_switch.enable(t)
    
    D2_imaging_dur = eval("MLOOP_PREPARATION_EIT_DURATION")

    t += D2_imaging_dur
    utils.jump_from_previous_value(D1_aom_power, t, 0.0)
    D1_aom_switch.disable(t)
    utils.jump_from_previous_value(sacher_aom_power, t, 0.0)
    sacher_aom_switch.disable(t)
    utils.jump_from_previous_value(op_aom_power, t, 0)#1)#0.7)#2)
    op_aom_switch.disable(t)
    
    t+= 20e-6
    # time_difference = D2_EIT_HEATING_DURATION - total_cooling_duration
    # if time_difference >0:
    #     t+= time_difference
    #####################################################################################

    #####################################################################################
    ### Forth ATOM IMAGE   
    t += GATE_TIME # add time between different kinetic shots
    t += EXTRA_RESORTING_TIME
    # t += GATE_TIME # add time between different kinetic shots

    hamamatsu.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)# trigger_duration = ((probe_duration + repeat_dead_time )*N_repeat+1e-3))#50e-6)
    
    # #######################################################################################
    # utils.jump_from_previous_value(fluorescence_aom_power, t, SA_FLUORESCENCE_POWER)#SA_FLUORESCENCE_POWER_SEC)
    # fluorescence_aom_switch.enable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # # utils.jump_from_previous_value(motl_aom_power, t, FLUORESCENCE_MOT_POWER_TEST)
    # # motl_aom_switch.enable(t + 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, SA_FLUORESCENCE_REPUMP_POWER)#SA_FLUORESCENCE_REPUMP_POWER_SEC)#2)
    # repump_aom_switch.enable(t+ 1.5e-6)
    # t += probe_duration_second_image#50e-6
    # utils.jump_from_previous_value(fluorescence_aom_power, t, 0.0)
    # fluorescence_aom_switch.disable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # utils.jump_from_previous_value(motl_aom_power, t, 0.0)
    # motl_aom_switch.disable(t+ 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, 0)
    # repump_aom_switch.disable(t+ 1.5e-6)
    # # mot_shutter.disable(t) ## Somehow having this here doesn't really work..?
    # t += repeat_dead_time 
    # #######################################################################################
    
    ################ D2 EIT IMAGING ################
    num_points = 1#MLOOP_EIT_COOLING_NUM_POINTS
    total_cooling_duration = 0

    D2_next_pi_AOM = eval("MLOOP_PREPARATION_EIT_PI_FREQ")
    laser_freq_jumping_box_ad9959.jump_frequency(t, "D1det", (D2_next_pi_AOM)*32*1e6, trigger=True)#SA_MOLASSES_FREQ*1e6, trigger=False)  

    t+=1e-3
    
    if D2_EIT_HEATING_SWITCH:
        utils.jump_from_previous_value(op_aom_power, t, MLOOP_PREPARATION_EIT_HEATING_POWER)#1)#0.7)#2)
        op_aom_switch.enable(t)
    sigma_pow = eval("MLOOP_PREPARATION_EIT_SIGMA_POWER")
    utils.jump_from_previous_value(sacher_aom_power, t, sigma_pow)#1)#0.7)#2)
    sacher_aom_switch.enable(t)
    pi_pow = eval("MLOOP_PREPARATION_EIT_PI_POWER")
    utils.jump_from_previous_value(D1_aom_power, t, pi_pow)
    D1_aom_switch.enable(t)
    
    D2_imaging_dur = eval("MLOOP_PREPARATION_EIT_DURATION")

    t += D2_imaging_dur
    utils.jump_from_previous_value(D1_aom_power, t, 0.0)
    D1_aom_switch.disable(t)
    utils.jump_from_previous_value(sacher_aom_power, t, 0.0)
    sacher_aom_switch.disable(t)
    utils.jump_from_previous_value(op_aom_power, t, 0)#1)#0.7)#2)
    op_aom_switch.disable(t)
    
    t+= 20e-6
    # time_difference = D2_EIT_HEATING_DURATION - total_cooling_duration
    # if time_difference >0:
    #     t+= time_difference
    #####################################################################################

    #######################################################################################
    # Turn off the traps for a while to lose all atoms
    # utils.jump_from_previous_value(dt808_PiRamanCoupling, t, 0.0)
    # dt808_aom_switch.disable(t)
    dt808_PiRamanCoupling_switch.disable(t)
    tisaph_aom_switch.disable(t)
    tisaph2_aom_switch.disable(t)
    t += GATE_TIME
    # utils.jump_from_previous_value(dt808_PiRamanCoupling, t, SA_MOT_DT808_PI_POWER)
    dt808_aom_switch.enable(t)
    dt808_PiRamanCoupling_switch.enable(t)
    tisaph_aom_switch.enable(t)
    tisaph2_aom_switch.enable(t)
    #######################################################################################


    # #####################################################################################
    # ### TAKE BACKGROUND IMAGE for first image:
    # # hamamatsu.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)# trigger_duration = ((probe_duration + repeat_dead_time )*N_repeat+1e-3))#50e-6)

    # utils.jump_from_previous_value(fluorescence_aom_power, t, SA_FLUORESCENCE_POWER)
    # fluorescence_aom_switch.enable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # # utils.jump_from_previous_value(motl_aom_power, t, FLUORESCENCE_MOT_POWER_TEST)
    # # motl_aom_switch.enable(t + 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, SA_FLUORESCENCE_REPUMP_POWER)#2)
    # repump_aom_switch.enable(t+ 1.5e-6)
    # t += probe_duration#50e-6
    # utils.jump_from_previous_value(fluorescence_aom_power, t, 0.0)
    # fluorescence_aom_switch.disable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # utils.jump_from_previous_value(motl_aom_power, t, 0.0)
    # motl_aom_switch.disable(t+ 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, 0)
    # repump_aom_switch.disable(t+ 1.5e-6)
    # # mot_shutter.disable(t) ## Somehow having this here doesn't really work..?
    # t += repeat_dead_time 
    
    # t += GATE_TIME
    # #####################################################################################

    #####################################################################################
    # ### TAKE BACKGROUND IMAGE for second image:
    # hamamatsu.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)# trigger_duration = ((probe_duration + repeat_dead_time )*N_repeat+1e-3))#50e-6)
    # hamamatsu_glauber.expose(t - HC_CAM_DELAY_SA_FLUORESCENCE, name="absorption", frametype='atoms', trigger_duration = cam_trigger_dur)# trigger_duration = ((probe_duration + repeat_dead_time )*N_repeat+1e-3))#50e-6)
    
    # utils.jump_from_previous_value(fluorescence_aom_power, t, SA_FLUORESCENCE_POWER_SEC)
    # fluorescence_aom_switch.enable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # # utils.jump_from_previous_value(motl_aom_power, t, FLUORESCENCE_MOT_POWER_TEST)
    # # motl_aom_switch.enable(t + 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, SA_FLUORESCENCE_REPUMP_POWER_SEC)#2)
    # repump_aom_switch.enable(t+ 1.5e-6)
    # t += probe_duration_second_image#50e-6
    # utils.jump_from_previous_value(fluorescence_aom_power, t, 0.0)
    # fluorescence_aom_switch.disable(t + 1.5e-6)
    # ### if we use MOT light for imaging
    # utils.jump_from_previous_value(motl_aom_power, t, 0.0)
    # motl_aom_switch.disable(t+ 1.5e-6)
    # utils.jump_from_previous_value(repump_aom_power, t, 0)
    # repump_aom_switch.disable(t+ 1.5e-6)
    # # mot_shutter.disable(t) ## Somehow having this here doesn't really work..?
    # t += repeat_dead_time 
    
    # t += GATE_TIME
    #####################################################################################
    
    utils.jump_from_previous_value(z_coil, t, 0)
    utils.jump_from_previous_value(x_coil, t, 0.0)
    utils.jump_from_previous_value(y_coil, t, 0.0)

    ## Added 7th August 2023, we need some time after mot_shutter is disabled otherwise MOT is always off in sequence:
    mot_shutter.disable(t) # close MOT shutter
    repump_shutter.disable(t) # close repump shutter
    t+=5e-3

    # ######## Use this when DT is on in img
    # # get rid of atoms before the no atoms image
    # dt808_aom_switch.disable(t)
    # utils.jump_from_previous_value(dt808_aom_power, t, 0.0)
    # utils.jump_from_previous_value(dt808_PiRamanCoupling, t, 0.0)
    # t+=10e-6

    #######################################################################################

    t += reset_mot_singleatom(t)#reset_mot(t)#, reset_mot_duration = 0.1 )
    #t += 5e-6

    # spectrum_awg_808AOD.reset(t)
    t += 100e-6

    stop(t)

