#!/usr/bin/env python

import os
import subprocess as sp
import shlex
import time
import itertools as it
import logging
logging.basicConfig(filename='encodings.log', level=logging.INFO)


def find_files_based_on_extension_within_directory(directory, extension):
    '''Return a list containing files with the provided extension'''

    return [f for f in os.listdir(directory) if f.endswith(extension)]


def find_files_based_on_extension(directory, extension):
    files_found_abs = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if os.path.splitext(file)[1] == extension:
                files_found_abs += [os.path.join(root, file)]

    return sorted(files_found_abs)


def timeit(func):

    def timed(*args, **kw):
        t0 = time.time()
        result = func(*args, **kw)
        t1 = time.time()
        runtime = (t1 - t0) / 60
        logging.info('Function {func_name} runtime: {time} [min].'.format(
                     func_name=func.__name__, time=runtime))
        return result

    return timed


@timeit
def vp8_encode(inp_file, out_file=None):
    if out_file is None:
        inp_path, inp_name = os.path.split(inp_file)
        inp_name = os.path.splitext(inp_name)[0]
        out_name = '{inp}_vp8.webm'.format(inp=inp_name)
        out_file = os.path.join(inp_path, out_name)

    command = 'ffmpeg -i input_file -c:v libvpx -b:v 1M -c:a libvorbis output_file'  # 12.75min
    command = 'ffmpeg -i input_file -c:v libvpx -b:v 1M -c:a libvorbis -threads 3 output_file'
    command = command.replace('input_file', inp_file).replace('output_file', out_file)
    args = shlex.split(command)
    logging.info(('Encoding is started with the following command:\n', ' '.join(args)))
    process = sp.Popen(args)
    process.wait()


@timeit
def vp9_encode_2pass(inp_file, out_file=None, crf=33, num_cpu=4,
                     br_v='1400K', br_a='64k', speed=2, nofilter=0,
                     hqdn='2:1.5:3:2.25', gradfun='1:8', unsharp='5:5:1.0:3:3:0.0'):
    '''constrained quality encoding, maintains quality as long as bitrate can be
    lower than the provided value after -b:v. crf controls quality: enables constant
    quality mode and sets quality (0-63) lower values are better quality.
    If crf is set to 'no' then the VOD settings are used, the crf option will be omitted.
    speed 4 tells VP9 to encode really fast, sacrificing quality. Useful to speed up the first pass.
    speed 1 is a good speed vs. quality compromise. Produces output quality typically very close to speed 0, but usually encodes much faster.
    at bitrates, k=kilobit K=Kilobyte, M=MB'''

    os.system('rm -fr *pass*.log')

    if out_file is None:
        inp_path, inp_name = os.path.split(inp_file)
        inp_name = os.path.splitext(inp_name)[0]
        if nofilter:
            out_name = '{inp}_vp9_crf{crf}.webm'.format(inp=inp_name, crf=crf)
        else:
            out_name = '{inp}_vp9_crf{crf}_hqdn{hqdn}_gradfun{grad}_unsharp{sharp}.webm'.format(
                       inp=inp_name, crf=crf, hqdn=hqdn, grad=gradfun, sharp=unsharp)
        out_file = os.path.join(inp_path, out_name)

    print(inp_file, out_file)
    speed = str(speed)
    num_cpu = str(num_cpu)
    if isinstance(crf, str):
        crf = 'no'
    else:
        crf = str(crf)

    command_p1 = 'ffmpeg -y -i {in_file} -c:v libvpx-vp9 -pass 1 -b:v {br_v} ' \
                 '-crf {crf} -threads {num_cpu} -speed 4 -tile-columns 6 -frame-parallel 1 ' \
                 '-an -f webm /dev/null'
    command_p2 = 'ffmpeg -i {in_file} -c:v libvpx-vp9 -pass 2 -g 25 -b:v {br_v} ' \
                 '-crf {crf} -vf "yadif, hqdn3d={hqdn}, gradfun={grad}, unsharp={unsharp}" ' \
                 '-threads {num_cpu} -speed {speed} -tile-columns 6 -frame-parallel 1 ' \
                 '-auto-alt-ref 1 -lag-in-frames 25 -c:a libopus -b:a {br_a} ' \
                 '-f webm {out_file}'
    command_p1 = command_p1.format(in_file=inp_file, br_v=br_v, crf=crf, num_cpu=num_cpu)
    command_p2 = command_p2.format(in_file=inp_file, br_v=br_v, crf=crf, num_cpu=num_cpu,
                                   speed=speed, br_a=br_a, out_file=out_file,
                                   hqdn=hqdn, grad=gradfun, unsharp=unsharp)
    if crf == 'no':
        command_p1 = command_p1.replace('-crf no', '')
        command_p2 = command_p2.replace('-crf no', '')
    if gradfun == '0:0':
        command_p2 = command_p2.replace(', gradfun=0:0', '')
    if hqdn == 'luma_spatial=0':
        command_p2 = command_p2.replace(', hqdn=' + hqdn, '')
    if unsharp == '0:0:0.0:0:0:0.0':
        command_p2 = command_p2.replace(', unsharp=' + unsharp, '')


    args1 = shlex.split(command_p1)
    args2 = shlex.split(command_p2)
    if nofilter:
        i_vf = args2.index('-vf')
        args2 = args2[:i_vf] + args2[i_vf+2:]
    logging.info(('2 pass encoding is started with the following commands:\n', ' '.join(args1),
                  '\n', ' '.join(args2)))
    process = sp.Popen(args1)
    process.wait()
    process = sp.Popen(args2)
    process.wait()


if __name__ == '__main__':
    avi_files = find_files_based_on_extension_within_directory('./', 'avi')
    print(avi_files)
    for avi_file in avi_files:
        out_file = os.path.splitext(avi_file)[0] + '.webm'
        vp9_encode_2pass(avi_file, out_file=out_file, crf=31, num_cpu=6, br_v='1000K', br_a='96k', speed=1,
                         hqdn='luma_spatial=2', gradfun='1.0:16', unsharp='9:9:1.0:3:3:0.0')
    stop
    # strength: .51 to 64,  radius: 8-32
    gradfuns = ['0.51:32', '1.0:16']
    hqdns = ['luma_spatial=2']
    # luma 3-63 ODD!! but more than 11 is bad!! ,luma size no more than 25 chroma close to zero
    unsharps = ['9:9:1.0:3:3:0.0', '7:7:1.0:3:3:0.0']
    # final best ssettings are 'luma_spatial=2', '1.0:16', '9:9:1.0:3:3:0.0'

    for gradfun, hqdn, unsharp in it.product(gradfuns, hqdns, unsharps):
        # logging.info(('Current filters:', gradfun, hqdn, unsharp))
        vp9_encode_2pass('Horv.avi', crf=31, num_cpu=3, br_v='1000K', br_a='96k', speed=1,
                         hqdn=hqdn, gradfun=gradfun, unsharp=unsharp)
