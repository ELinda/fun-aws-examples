import os
import glob
import argparse
import random
import requests
import soundfile as sf

import boto3
import numpy as np


def get_puns():
    quotes_url = 'https://raw.githubusercontent.com/xasos/Puns/master/Backend/puns.json'
    quotes_json = requests.get(quotes_url).json()
    return [v['Pun'] for v in quotes_json]


def get_kicks_crashes(path_prefix='sample'):
    kicks = [get_soundfile_data_only(fpath) for fpath in glob.glob(os.path.join(path_prefix, 'kick*ogg'))]
    crashes = [get_soundfile_data_only(fpath) for fpath in glob.glob(os.path.join(path_prefix, 'crash*ogg'))]
    return kicks, crashes


def convert_to_ssml(string):
    """put emphasis on last two words"""
    sep = ' '
    split_index = string.rfind(sep, 0, string.rfind(sep))
    unemph = string[:split_index]
    emph_strong = string[split_index:]
    ssml_template = '<speak>%s <emphasis level="strong">%s</emphasis></speak>'
    ssml =  ssml_template % (unemph, emph_strong)
    print(ssml)
    return ssml


def get_rand_two_kicks_crash(kicks, crashes):
    """joke happened type sound effect"""
    two_kicks = random.sample(kicks, 2)
    one_crash = random.sample(crashes, 1)
    
    return np.concatenate(two_kicks + one_crash)


def save_joke_to_local(joke_name, data):
    with open(joke_name, 'wb') as file:
        file.write(data)


def get_joke_encoded_binary(polly, joke_text):
    # use default sample rate of 22050
    response = polly.synthesize_speech(VoiceId='Joanna',
                OutputFormat='ogg_vorbis',
                TextType='ssml',
                Text=joke_text)
    return response['AudioStream'].read()


def get_joke_file_name(output_path, joke_text):
    # re find may be more suitable
    joke_name = '_'.join(joke_text.lower().replace('-', '').split(' ')[1:4]) + '.ogg'
    return os.path.join(output_path, joke_name)


def get_soundfile_data_only(file_name):
    data, sr = sf.read(file_name)
    if len(data.shape) > 1 and data.shape[1] == 2:
        return (data[0] + data[1])/2
    return data


def add_sound_effect(file_name, kicks, crashes):
    data, sr = sf.read(file_name)
    data_with_end = np.concatenate([data, get_rand_two_kicks_crash(kicks, crashes)])
    sf.write(file_name, data_with_end, sr)



def get_parsed_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', required=True,
                        help='output folder')
    return parser.parse_args()


if __name__ == "__main__":
    puns = get_puns()
    kicks, crashes = get_kicks_crashes()
    output_path = get_parsed_args().output

    sess = boto3.Session(region_name='us-east-1')
    polly = sess.client('polly')

    for pun in puns:
        joke_binary = get_joke_encoded_binary(polly, joke_text=convert_to_ssml(pun))
        file_name = get_joke_file_name(output_path, pun)
        save_joke_to_local(file_name, joke_binary)
        add_sound_effect(file_name, kicks, crashes)
        print('%s output' % (file_name))