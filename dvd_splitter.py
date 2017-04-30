#!/usr/bin/env python3

import shlex
import subprocess as sp


class DVD():

    def __init__(self, dvd_dirname='VIDEO_TS'):
        self.dvd_dirname = dvd_dirname
        self.split_dvd()

    @property
    def titles_chapters(self):
        comm_id = 'mplayer -dvd-device {dvd}/ dvd://1 -identify -frames 0'.format(dvd=self.dvd_dirname)
        p1 = sp.run(shlex.split(comm_id), stdout=sp.PIPE, universal_newlines=True)
        lines = p1.stdout.split('\n')
        # print('\n'.join(lines))
        try:
            n_titles = [int(line.split('=')[1]) for line in lines
                        if line.startswith('ID_DVD_TITLES')][0]
        except:
            print('No titles found!')
            return
        titles_chaps = []
        for i in range(1, n_titles + 1):
            pattern = 'ID_DVD_TITLE_{0}_CHAPTERS'.format(i)
            n_chapters = [int(line.split('=')[1]) for line in lines if line.startswith(pattern)][0]
            titles_chaps.append((i, n_chapters))

        return titles_chaps

    def split_dvd(self):
        comm_split = ('mplayer -dvd-device {dvd}/ dvd://1 -title {itit}-{itit} '
                      '-chapter {ichap}-{ichap} -dumpstream -dumpfile {vob}')
        for ititle, n_chaps in self.titles_chapters:
            for ichapter in range(1, n_chaps + 1):
                vob_file = 'title{0:02d}_chapter{1:02d}.vob'.format(ititle, ichapter)
                comm = comm_split.format(dvd=self.dvd_dirname, itit=ititle, ichap=ichapter,
                                         vob=vob_file)
                print('Processing', ititle, ichapter, comm)
                process = sp.Popen(shlex.split(comm))
                process.wait()
                print('Extracted:', vob_file)


if __name__ == '__main__':
    DVD()
