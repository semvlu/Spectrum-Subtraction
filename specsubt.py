import numpy as np
import scipy.signal as signal
import os
import soundfile as sf
import librosa
base_path = os.getcwd()
output_path = os.path.join(base_path, "subt_sig.wav")

def resample(input_signal, old_smaple_rate, new_sample_rate):
    resampled_signal = signal.resample_poly(input_signal, old_smaple_rate, new_sample_rate)
    return resampled_signal.astype(input_signal.dtype)

def stft(audio, dimension):
    dimensions= audio.ndim
    transform= np.array([], ndmin=1)
    if (dimensions==1):
        transform= librosa.stft(audio) #mono
    else:
        transform= librosa.stft(audio[:, dimension]) #stereo
    return transform

def spec_subt(noise_profile_n, input_signal_y, dimension):
    N= stft(noise_profile_n, dimension)
    noise_mag= np.abs(N) #mag spectrum

    Y= stft(input_signal_y, dimension)
    input_mag= np.abs(Y)
    phase_spec= np.angle(Y) # phase spectrum
    phase_info= np.exp(1.0j * phase_spec) # phase info

    #spectral subtraction
    noise_mean= np.mean(noise_mag, axis=1, dtype= "float64") #find noise mean
    noise_mean= noise_mean[:, np.newaxis] #perform subtraction
    output_X= input_mag - noise_mean
    X= np.clip(output_X, a_min=0.0, a_max=None)

    #add phase info
    X= X * phase_info

    #inverse STFT
    output_x= librosa.istft(X)
    return output_x

def run(noise_profile, noisy_input, FS):
    # read noise profile, input and find dimensions
    n, fs_n= sf.read(noise_profile)
    y, fs_y= sf.read(noisy_input)
    profile_dimensions= n.ndim
    input_dimensions= y.ndim

    if (fs_n != FS):
        n= resample(n, fs_n, FS)
    if (fs_y != FS):
        y= resample(y, fs_y, FS)    
    
    assert profile_dimensions <= 2, "Only mono and stereo files supported"
    assert input_dimensions <= 2, "Only mono and stereo files supported"

    if (profile_dimensions > input_dimensions):
        # make noisy input stereo file
        num_channels= profile_dimensions
        y= np.array([y,y], ndim= num_channels)
        y= np.moveaxis(y, 0, 1)

    else:
        # make noise profile stereo file
        num_channels= input_dimensions
        if (profile_dimensions != input_dimensions):
            n= np.array([n,n], ndmin= num_channels)
            n= np.moveaxis(n, 0, 1)

    # find output for each channel
    for channel in range(num_channels):
        single_channel_output= spec_subt(n, y, channel)
        if (channel==0):
            output_x= np.zeros((len(single_channel_output), num_channels)) 
        output_x[:, channel]= single_channel_output

    # convert to mono
    if (num_channels > 1):
        output_x= np.moveaxis(output_x, 0, 1)
        output_x= librosa.to_mono(output_x)

    # write to wav
    sf.write(output_path, output_x, FS, format="WAV")
    return


