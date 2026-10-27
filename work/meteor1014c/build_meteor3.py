"""Meteor's impact covers the battlefield: build_meteor2.py's build with PC0010_Meteor_Impact's sphere 150 m around the
target (the game's biggest, Titan's stamp wave) instead of 45 m.
    build_meteor3.py <out dir> <json in> <json out>"""
import sys
sys.path.insert(0, '/work/meteor1014b')
import build_meteor2 as M
M.IMPACT['CollisionParameter_Array'] = [15000.0]
if __name__ == '__main__':
    M.main()
