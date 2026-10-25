"""Fifty intentional cue pictograms, baked at build time; no extra Pi dependency.

Each symbol is drawn directly on the same 32x32 pixel grid as the original vocabulary.
Category silhouettes remain related, but each selectable cue has a distinct semantic mark.
"""
import math


def build_cue_icons(Canvas, originals):
    icons = {}

    def new(key, base=None):
        c = originals[base]() if base else Canvas()
        icons['cue_' + key] = c
        return c

    def line(c, x0, y0, x1, y1, width=2, value=1):
        steps = max(abs(x1-x0), abs(y1-y0), 1)
        for n in range(steps + 1):
            x, y = round(x0+(x1-x0)*n/steps), round(y0+(y1-y0)*n/steps)
            c.rect(x, y, x+width-1, y+width-1, value)

    def mouth(c, shape='open'):
        if shape == 'open': c.ring(16, 21, 4, 5, 2)
        elif shape == 'sad': c.arc(16, 25, 5, 205, 335, 2)
        else: c.arc(16, 17, 7, 10, 170, 2)

    def face(c):
        c.ring(16, 16, 12, 13, 2)
        c.ellipse(11, 13, 1.5, 2); c.ellipse(21, 13, 1.5, 2)

    def rays(c, side=26):
        for y in (10, 16, 22): line(c, side, y, min(29, side+3), y)

    def horn(c, x=4, y=8, size=1):
        c.polygon([(x,y+6),(x+7,y+6),(x+15,y),(x+15,y+18),(x+7,y+12),(x,y+12)])
        c.polygon([(x+2,y+8),(x+8,y+8),(x+13,y+4),(x+13,y+14),(x+8,y+10),(x+2,y+10)],0)

    def wheels(c, y=24):
        c.ring(9,y,4,4,2); c.ring(24,y,4,4,2)

    def car(c, y=8):
        c.round_frame(3,y+8,29,y+16,3)
        c.polygon([(8,y+8),(12,y),(22,y),(27,y+8)])
        c.polygon([(11,y+7),(14,y+2),(20,y+2),(23,y+7)],0)
        wheels(c,y+17)

    def cloud(c):
        c.round_rect(4,9,28,18,4)
        c.ellipse(11,11,6,6); c.ellipse(20,10,6,7)

    new('fire_smoke','smoke')
    new('emergency_siren','siren')
    c=new('civil_siren'); c.rect(13,18,16,30); horn(c,3,3); line(c,23,7,29,4); line(c,24,15,30,15); line(c,23,23,29,26)
    c=new('car_horn'); horn(c); rays(c)
    c=new('truck_horn'); horn(c,2,3); horn(c,9,12); c.rect(2,25,8,28)
    c=new('reverse_beep'); c.round_frame(10,8,29,23,3); c.rect(12,23,15,27); c.rect(24,23,27,27); c.polygon([(10,15),(4,10),(4,13),(1,13),(1,17),(4,17),(4,20)]); c.rect(15,12,18,15); c.rect(22,12,25,15)
    c=new('breaking'); c.polygon([(4,4),(15,4),(12,13),(17,17),(10,27)]); c.polygon([(19,3),(28,6),(24,16),(19,13)]); c.polygon([(23,20),(29,19),(28,29),(16,29)]); line(c,4,6,5,20,value=0)
    c=new('scream'); face(c); mouth(c); line(c,1,8,3,5); line(c,28,5,30,8)
    c=new('explosion','bang'); c.rect(15,9,16,19); c.rect(15,22,16,24)
    c=new('tire_squeal'); c.ring(17,11,8,9,3); c.ring(17,11,3,4,1); line(c,10,20,5,24); line(c,5,24,10,27); line(c,10,27,6,30); line(c,22,20,17,24); line(c,17,24,22,27); line(c,22,27,18,30)

    new('name_called','name')
    c=new('doorbell'); c.round_frame(8,2,24,30,4); c.ring(16,20,5,5,2); c.rect(13,6,19,8); line(c,2,11,4,9); line(c,28,9,30,11)
    new('knock','knock')
    c=new('phone_ring'); c.round_frame(9,3,23,29,3); c.rect(13,6,19,7); c.rect(14,25,18,26); c.arc(11,16,9,145,215); c.arc(21,16,9,325,35)
    c=new('baby_cry'); c.ring(16,17,11,11,2); c.arc(15,6,5,210,340); c.ellipse(11,15,1.5,1.5); c.ellipse(21,15,1.5,1.5); mouth(c); c.polygon([(3,17),(1,22),(5,22)]); c.polygon([(29,17),(27,22),(31,22)])
    c=new('children_shout'); c.ring(11,13,7,8,2); c.ring(23,19,7,8,2); c.rect(8,11,9,12); c.rect(13,11,14,12); c.ellipse(11,16,2,2); c.rect(20,17,21,18); c.rect(25,17,26,18); c.ellipse(23,22,2,2); line(c,1,3,4,6); line(c,26,3,29,6)
    c=new('speech'); c.round_frame(3,5,28,23,5); c.polygon([(8,22),(14,22),(6,29)]); c.rect(8,11,23,12); c.rect(8,16,19,17)
    c=new('human_whistle'); c.arc(13,15,11,70,300); c.rect(17,17,23,20); c.ellipse(10,11,1.5,1.5); line(c,25,11,29,8); line(c,26,18,30,18); line(c,25,25,29,28)
    c=new('crying'); face(c); mouth(c,'sad'); c.polygon([(8,16),(5,22),(10,22)]); c.polygon([(24,16),(21,22),(26,22)])
    c=new('clap'); c.polygon([(4,20),(2,15),(4,13),(9,17),(8,6),(11,5),(14,19),(19,25),(16,29),(9,27)]); c.polygon([(18,18),(16,7),(19,5),(22,18),(25,13),(28,14),(27,24),(22,29),(18,25)]); line(c,8,0,10,2); line(c,21,0,23,2); c.rect(28,4,30,6)

    new('alarm_clock','clock')
    c=new('microwave'); c.round_frame(2,6,30,26,3); c.round_frame(5,9,23,23,2); c.rect(26,10,27,12); c.rect(26,16,27,20); line(c,9,14,12,11); line(c,13,19,18,14)
    c=new('device_beep'); c.round_frame(5,13,26,28,3); c.rect(10,18,12,20); c.rect(16,18,21,20); c.arc(16,13,8,215,325); c.arc(16,13,13,220,320)
    c=new('boiling'); c.round_frame(5,13,27,28,4); c.rect(2,12,29,14); c.ring(11,21,2,2,1); c.ring(20,23,3,3,1)
    for x in (10,17,24): line(c,x,2,x-2,5); line(c,x-2,5,x,8)
    c=new('faucet'); c.rect(3,10,25,14); c.rect(3,10,7,28); c.rect(21,14,25,19); c.rect(11,5,15,10); c.rect(8,4,18,6); c.polygon([(23,21),(19,28),(27,28)])
    c=new('drip','drop'); c.arc(16,26,13,25,155); c.arc(16,27,9,25,155)
    c=new('door'); c.rect(4,3,6,29); c.rect(4,2,25,4); c.rect(24,3,26,29); c.polygon([(7,5),(20,9),(20,30),(7,27)]); c.polygon([(9,8),(18,11),(18,27),(9,25)],0); c.ellipse(15,18,1.5,1.5)
    c=new('slam'); c.round_frame(8,3,24,29,1); c.ellipse(19,18,1.5,1.5)
    for y in (7,16,25): line(c,1,y-2,5,y); line(c,27,y,30,y-2)
    c=new('keys'); c.ring(10,10,7,7,3); line(c,14,15,27,28,3); line(c,23,23,27,19,3); line(c,18,19,21,16,3); c.ring(20,7,5,5,2)
    c=new('dishes'); c.ring(14,17,11,11,2); c.ring(14,17,7,7,2); c.rect(28,5,29,28); c.rect(25,5,26,12); c.rect(25,11,29,13)

    c=new('traffic'); car(c,3); line(c,1,30,10,30); line(c,18,30,28,30); c.rect(1,6,6,8); c.rect(25,5,30,7)
    c=new('passing_car'); car(c,4); c.rect(1,2,11,3); c.rect(1,6,7,7); c.rect(22,28,30,29)
    c=new('motorcycle'); wheels(c,23); line(c,9,23,15,13); line(c,15,13,23,23); line(c,9,23,23,23); line(c,15,13,21,13); line(c,21,13,24,8); line(c,22,7,28,7); c.rect(10,10,16,12)
    c=new('bus'); c.round_frame(5,3,27,27,4); c.rect(8,7,24,16); c.rect(15,7,16,16,0); c.rect(9,20,12,22); c.rect(21,20,24,22); c.rect(8,27,11,30); c.rect(22,27,25,30)
    c=new('train'); c.round_frame(6,3,26,25,5); c.rect(10,7,22,14); c.rect(15,7,16,14,0); c.ring(16,20,3,3,1); line(c,10,25,5,30); line(c,22,25,27,30); c.rect(8,28,24,29)
    c=new('train_horn'); c.rect(4,14,23,21); c.rect(12,7,20,14); c.rect(2,22,27,24); c.ring(9,27,3,3,1); c.ring(22,27,3,3,1); line(c,3,4,7,7); line(c,14,1,14,4); line(c,23,4,27,2)
    c=new('bicycle_bell'); c.ring(16,12,8,8,2); c.rect(9,20,23,22); c.rect(15,21,17,29); c.rect(11,28,22,30); line(c,23,7,27,4); c.rect(25,3,29,5); c.arc(16,12,13,190,240)
    c=new('footsteps'); c.ellipse(11,12,4,8); c.ellipse(22,23,4,7); c.rect(8,22,13,26); c.rect(19,9,24,12)
    c=new('running'); c.ellipse(19,5,3,3); line(c,17,10,13,17,3); line(c,13,12,7,9); line(c,17,11,23,15); line(c,23,15,28,12); line(c,14,17,21,22,3); line(c,21,22,17,29,3); line(c,13,18,8,24,3); line(c,8,24,2,24,3)
    c=new('engine_start'); c.round_frame(4,11,27,26,3); c.rect(8,7,18,11); c.rect(1,15,4,23); c.rect(26,14,30,19); c.polygon([(18,12),(11,21),(16,21),(13,29),(23,18),(18,18)])

    new('dog_bark','dog')
    c=new('dog_vocal'); c.polygon([(8,8),(3,3),(4,19),(9,24),(18,28),(25,24),(21,16),(17,11)]); c.polygon([(9,13),(7,9),(6,18),(10,22),(18,25),(22,23),(19,18),(16,14)],0); c.ellipse(13,15,1.5,1.5); c.ellipse(23,18,3,2); line(c,25,9,29,6); line(c,27,14,30,14)
    c=new('cat_meow'); c.polygon([(4,4),(12,9),(20,9),(28,4),(27,22),(23,28),(9,28),(5,22)]); c.polygon([(7,9),(12,12),(20,12),(25,9),(24,21),(21,25),(11,25),(8,21)],0); c.ellipse(11,17,1.5,2); c.ellipse(21,17,1.5,2); c.polygon([(13,21),(19,21),(16,24)]); line(c,1,19,7,21); line(c,25,21,30,19)
    c=new('bird'); c.ellipse(16,18,9,10); c.ellipse(22,10,6,6); c.polygon([(26,8),(32,11),(26,13)]); c.ellipse(23,9,1.5,1.5,0); c.polygon([(8,17),(1,12),(3,24),(10,25)]); c.arc(17,17,6,20,170); c.rect(13,26,14,30); c.rect(20,26,21,30)
    c=new('rain'); cloud(c)
    for x in (8,16,24): line(c,x,22,x-2,28)
    c=new('thunder'); cloud(c); c.polygon([(17,16),(11,25),(16,25),(13,32),(24,21),(18,21)])
    c=new('wind'); line(c,2,10,22,10); c.arc(23,7,5,180,360); line(c,2,17,27,17); c.arc(26,21,5,270,90); line(c,4,24,15,24); c.arc(15,27,4,270,90)
    new('music','music')
    c=new('saxophone'); c.polygon([(18,2),(26,2),(26,5),(22,5),(22,22),(18,28),(10,29),(5,25),(4,17),(9,17),(9,23),(12,25),(16,24),(18,21)]); c.rect(19,7,20,18,0); c.ellipse(16,12,2,1); c.ellipse(16,17,2,1); c.polygon([(1,10),(11,10),(9,19),(4,19)]); c.rect(2,11,10,12,0)
    c=new('laughter'); face(c); mouth(c,'laugh'); c.rect(10,17,22,19); c.ellipse(16,22,4,3); c.rect(10,11,12,12); c.rect(20,11,22,12)
    return icons
