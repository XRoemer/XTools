#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) [2022] [Xaver Römer], [YOUR EMAIL]
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

"""
Some Tools For Handling Guidelines And Correcting Paths/Strokes
"""



'''
        DEBUGGING 
    Used with Eclipse and PyDev
    start the pydev Server and
    use pd() in your code to start PyDev's Debugger
'''
import sys
platform = sys.platform
from traceback import format_exc as tb

class pydevBrk():  
    # adjust your path to PyDevs Folder pysrc
    if platform == 'linux':
        sys.path.append('/opt/eclipse/plugins/org.python.pydev_3.8.0.201409251235/pysrc')  
    else:
        sys.path.append(r'C:\Users\Boon\.p2\pool\plugins\org.python.pydev.core_9.3.0.202203051235\pysrc')  

    def run(self):
        from pydevd import settrace
        settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True) 
pd = pydevBrk().run

# use print_info for output in running inkscape (for windows)
def print_info(text):
    realout   =sys.stdout    # re-map script output to stderr - so can be seen by user
    sys.stdout=sys.stderr
    txt = ""
    if isinstance(text,list):
        for t in text:
            txt += str(t) + "\n"
        print(txt)
    else:
        print(text)

    
'''    DEBUGGING END '''
    

import inkex
from inkex.elements import Guide
from inkex.paths import Move, Line

import os.path
import json, math



class XTools(inkex.EffectExtension):
        
    def set_parser(self,name,default,help):
        if default in [False,True]:
            self.arg_parser.add_argument(
                "--{}".format(name),
                dest=name,
                type=inkex.Boolean, 
                default=default,
                help=help,
            )
        else:
            self.arg_parser.add_argument(
                "--{}".format(name),
                dest=name,
                default=default,
                help=help,
            )
            
        
    def add_arguments(self, pars):
        
        args2parseTAB1 = [
            ["clean_glines",     True,   "clean guidelines"],
            ["thresh_gl",        "0.2",  "set threshold"],
            ["find_reg",         False,  "search for repeated distances"],
            ["thresh_reg",       "0.2",  "set threshold"],
            ["name_glines_on",   False,  "set position of g-lines as description"],
            ["name_glines_off",  False,  "delete description"],
            ]
        args2parseTAB2 = [
            ["select_all",     False,  "true selects all, false uses selected"],
            ["set_gl_to_knots",False,   "set gl to crossings"],
            ["thresh_crossings","0.2",  "set threshold"],
            ["set_path_to_gl", False,   "set path to closest point on g-line"],
            ["thresh_path_to_gl","0.2",  "set threshold"],
            ]
        args2parseTAB3 = [
            ["tab",             "clean_gl", ""],
            ["dist_top",        "10",       "set distance between first horizontal guideline and top of document. empty means 0."],
            ["delete_glines",   True,       "delete old guidelines"],
            ["dist_left",       "10",       "set distance between first vertical guideline and left border of document. empty means 0."],
            ["lines_distanceh", "12,6,12,30","set distances between horizontal guidelines."],
            ["lines_distancev", "12,6,12,30","set distances between vertical guidelines."],
            ["repeath",         "5",        "set horizontal repetitions"],
            ["repeatv",         "5",        "set vertical repetitions"],
            ]
        args2parseTAB4 = [
            ["clear_glines",   False,     "remove existing guidelines"],
            ["slot_nr",        "0",       "set slot number to read from or to write to"],
            ["gset_name",       "",       "optional: name for saved guidelines. will be shown in the info"],
            ["use_read_or_write",False,   "enable reading/writing"],
            ["read_or_write",   False,    "import glines to document or save current guidelines to file"],
            ["folder",          "",       "path to folder to read from or to write to"],
            ["filename",        "glines", "filename to read from and write to"],
            ["get_info",        False,    "get information about used slots"],
            ]
        
        for a in args2parseTAB1:
            self.set_parser(*a)
        for a in args2parseTAB2:
            self.set_parser(*a)
        for a in args2parseTAB3:
            self.set_parser(*a)
        for a in args2parseTAB4:
            self.set_parser(*a)
            
            
    def effect(self):
        
        o = self.options
        
        match self.options.tab:
            
            case "clean_gl":
                if o.clean_glines:
                    self.clean_glines()
                if o.find_reg:
                    self.find_regularities()
                if o.name_glines_on:
                    self.set_guides_description()
                if o.name_glines_off:
                    self.remove_guides_description()
                                    
            case "correct_paths":
                if o.set_gl_to_knots:
                    self.correct_paths()
                elif o.set_path_to_gl:
                    self.get_closest_point_on_gl()                
            
            case "irr_gl":
                if o.delete_glines:
                    self.remove_glines()
                self.set_irregular_guidelines()
                
            case "save_glines":
                if o.get_info:
                    self.get_info()
                    return
                if o.clear_glines:
                    self.remove_glines()
                if o.use_read_or_write:
                    if o.read_or_write:
                        self.save_glines()
                    else:
                        self.read_glines()
        
        
    def get_guides(self):
        
        guides =  self.svg.namedview.get_guides()
        guides_h = []
        guides_v = []
        
        for g in guides:
            
            x = g.point.x
            y = self.y_cor(g.point.y)
            
            if g.is_horizontal:
                guides_h.append([y,g])
            else:
                guides_v.append([x,g])
        
        guides_h.sort(key = lambda x: x[0])
        guides_v.sort(key = lambda x: x[0])             
        return guides_h,guides_v   
     
    def set_irregular_guidelines(self):
        
        dist_top = float(self.options.dist_top)
        dist_left = float(self.options.dist_left)
        disth = list([float(a) for a in self.options.lines_distanceh.split(",")])
        distv = list([float(a) for a in self.options.lines_distancev.split(",")])
        repsh = int(self.options.repeath)
        repsv = int(self.options.repeatv)
        
        x = dist_left
        y = dist_top
        
        bbox_h = self.svg.get_page_bbox().height 
        
        for r in range(repsh):
            for d in disth:
                y1 = -y + bbox_h
                self.draw_guide(0,y1,[0,1])
                y += d
            y1 = -y + bbox_h
            self.draw_guide(0,y1,[0,1])
                
        for r in range(repsv):
            for d in distv:
                self.draw_guide(x,bbox_h,[1,0])
                x += d
            self.draw_guide(x,bbox_h,[1,0])
        
    def get_closest_point(self,gtype,point,guides):
        
        dist = [[abs(g[0] - point),nr] for nr,g in enumerate(guides)]
        dist.sort()
        shortest = dist[0][1]
        sh = guides[shortest]
        return guides[shortest][0] 
        
    def correct_paths(self):
        
        paths = self.get_selected_paths()
        guides_h,guides_v = self.get_guides()         

        for p in paths:
            arrs = []
            arr2 = []
            
            arrs = [[a.x,a.y] for a in p.get_path().to_non_shorthand()]
                   
            for i in range(len(arrs)):
                x = arrs[i][0]
                y = arrs[i][1]
                x2 = self.get_closest_point("x",x, guides_v)
                y2 = self.get_closest_point("y",y, guides_h) 
                
                if i == 0:
                    arr2.append(Move(x2,y2))
                else:
                    arr2.append(Line(x2,y2))
            p.set_path(arr2)
            
    def get_closest_point_on_gl(self):
        
        try:
            guides =  self.svg.namedview.get_guides()
            guide_points = []
            for g in guides:
                guide_points.append([g.point.x,g.point.y,math.degrees(g.orientation.angle)])
            
            paths = self.get_selected_paths()          
            for path in paths:
                new_points = self.calc_dist_point_gl(path,guide_points)
                self.set_path(path,new_points)    
        except:
            err = tb()
            print_info(err)
            
    def calc_dist_point_gl(self,path,guide_points):
        
        new_points = []
        for nr,p in enumerate(path.get_path().to_non_shorthand()):
            px = p.x
            py = p.y
            py = self.y_cor(py)
            
            distances = []
            
            for nr,g in enumerate(guide_points):
                gx,gy,angle = guide_points[nr]
                dx = gx-px
                dy = gy-py
                
                angle_hor_path_pxy_gxy = math.degrees(math.atan(dy/dx))  

                angle_hor_gline = angle
                angle_perpendicular_path_pxy_gxy = angle_hor_gline - angle_hor_path_pxy_gxy 
                beta = 90 - angle_perpendicular_path_pxy_gxy

                c = math.sqrt(dx**2 + dy**2)
                len_perpendicular = c * math.sin(math.radians(beta))

                if dx < 0:
                    len_perpendicular = -len_perpendicular
                
                distances.append([abs(len_perpendicular),len_perpendicular,[px,py],angle_hor_gline])
                
            distances.sort()
                    
            if distances[0][0] > float(self.options.thresh_path_to_gl):
                px,py = distances[0][2]
                py = self.y_cor(py)
                new_points.append([px,py])
            else:
                newx,newy = self.calc_point_on_gl(*distances[0][1:])
                new_points.append([newx,newy])
           
        return new_points
    
    def calc_point_on_gl(self,len_perpendicular,point,beta):
        
        alpha = 90 - beta
        b = len_perpendicular * math.sin(math.radians(beta))
        a = len_perpendicular * math.sin(math.radians(alpha))
        px,py = point
        
        return px+a,self.y_cor(py+b)
    
    def clean_glines(self):
        
        try:
            
            horiz = [0]
            verticals = [0]
            thresh = float(self.options.thresh_gl)
            
            guides_h,guides_v = self.get_guides()
            
            for y, guide in guides_h:
                if y - horiz[-1] < thresh:
                    guide.delete()
                    continue
                horiz.append(y)
                guide.delete()
                    
            for _, guide in guides_v:    
                    
                x = guide.point.x
                if x - verticals[-1] < thresh:
                    guide.delete()
                    continue
                verticals.append(x)
                guide.delete()
            
            horiz.pop(0)
            verticals.pop(0)
            horiz.sort()
            verticals.sort()
    
            orientation = (0,1)
            for y in horiz:
                y2 = -y + self.svg.get_page_bbox().height 
                g = self.draw_guide(0,y2,orientation)                
            orientation = (1,0)
            for x in verticals:
                self.draw_guide(x,0,orientation)
            
        except:
            err = tb()
            print(err)
    
    def find_regularities(self):
        
        try:
            guides_h,guides_v = self.get_guides()
            horiz = [-500]
            verticals = [-500]
            
            for _, guide in guides_h:
                y = guide.point.y
                horiz.append(y)
                guide.delete()
                    
            for _, guide in guides_v:    
                x = guide.point.x
                verticals.append(x)
                guide.delete()
            
            threshv = float(self.options.thresh_reg)
            verticals = self._find_regularities(verticals,threshv)
            horiz = self._find_regularities(horiz,threshv)
            
            horiz.pop(0)
            verticals.pop(0)
            
            orientation = (0,1)
            for y in horiz:
                self.draw_guide(0,y,orientation)
                
            orientation = (1,0)
            for x in verticals:
                self.draw_guide(x,0,orientation)
        except:
            err = tb()
            print(err)
        
    def _find_regularities(self, vals,thresh):
        
        dist = [[vals[nr+1]-vals[nr],nr+1] for nr,h in enumerate(vals) if nr < len(vals)-1]
        dist.insert(0,[vals[0],0])
        dist.sort()
        
        new_list = []
        old_val = 0
        nr = 0
        
        for d in dist:
            if len(new_list) == 0:
                new_list.append([d])
                old_val = d[0]
                continue
            if d[0] - old_val < thresh:
                new_list[nr].append(d)
            else:
                new_list.append([d])
                nr += 1
            old_val = d[0]
        
        new_list2 = []
            
        for li in new_list:
            val = 0
            for el in li:
                val += el[0]
            schnitt = round(val / len(li),1)
            temp = []
            for el in li:
                new_list2.append([schnitt,el[1]])
 
        new_list2.sort(key = lambda x: x[1])
        new_list3 = []
        val = 0
        for n in new_list2:
            val += n[0]
            new_list3.append(round(val,1))
            
        return new_list3
    
    def save_glines(self):

        guides =  self.svg.namedview.get_guides()
        slot_dict = {}
        slot_dict["name"] = self.options.gset_name
        slot_dict["values"] = {}
        try:
            for nr,g in enumerate(guides):
                slot_dict["values"][nr] = {}
                p = g.point
                o = g.orientation
                slot_dict["values"][nr]["point"] = [p.x,p.y]
                slot_dict["values"][nr]["orientation"] = [o.x,o.y]                            
            
            path = os.path.join(self.options.folder, self.options.filename + ".json")
            
            if os.path.exists(path):
                with open(path) as json_file:
                    saved_slot_dict = json.load(json_file)
                saved_slot_dict[self.options.slot_nr] = slot_dict
                
                json_string = json.dumps(saved_slot_dict, indent=4)
                with open(path, 'w') as outfile:
                    outfile.write(json_string)
                
            else:
                ddict = {}
                ddict[self.options.slot_nr] = slot_dict
                json_string = json.dumps(ddict, indent=4)
                with open(path, 'w') as outfile:
                    outfile.write(json_string)
                
        except:
            err = tb()
            print_info(err)
    
    def read_glines(self):
        
        try:
            path = os.path.join(self.options.folder, self.options.filename + ".json")
            if not os.path.exists(path):
                print_info("path doesn't exist")
                return
            
            with open(path) as json_file:
                saved_slot_dict = json.load(json_file)
            
            slot_nr = str(self.options.slot_nr)
            if slot_nr in saved_slot_dict:
                slot_dict = saved_slot_dict[slot_nr]
            else:
                print_info("slot nr doesnt exist")
                return
            
            vals = slot_dict["values"]
            for v in vals:
                x,y = vals[v]["point"]
                ox,oy = vals[v]["orientation"]
                self.draw_guide(x,y,[ox,oy])
        except:
            err = tb()
            print_info(err)    
            
    def get_info(self):
        
        path = os.path.join(self.options.folder, self.options.filename + ".json")
        if not os.path.exists(path):
            print_info("path doesn't exist")
            return
        
        with open(path) as json_file:
            saved_slot_dict = json.load(json_file)
        
        txt = ""
        
        for nr in sorted(saved_slot_dict.keys()):
            name = saved_slot_dict[nr]["name"]
            txt += "slot nr {}    name: {} \n".format(nr,name)
            
        print_info(txt)
        
            
    ### OVERALL USED METHODS
    
    def y_cor(self,y):
        # # fix for borked guide coordinates, because Inkscape 
        # # and inkex use wrong coordinates that are relative to the document height
        return -y + self.svg.get_page_bbox().height 
    
    def set_path(self,path,points):
        move = Move(*points[0])
        lines = []
        for i in range(len(points)-1):
            lines.append(Line(*points[i+1]))
        path.set_path([move, *lines])
    
    def get_selected_paths(self):
        if self.options.select_all:
            idpaths = [i for i in self.svg.get_ids() if "path" in i]
            paths =  [self.svg.getElementById(i) for i in idpaths]
        else:
            paths =  [p for p in self.svg.selection.values()]
        return paths

    def remove_glines(self):
        guides =  self.svg.namedview.get_guides()
        for g in guides:
            g.delete()
        
    def draw_guide(self,x1,y1,orientation1):    
        new_guide = Guide().move_to(x1, y1 , orientation1)
        self.svg.namedview.add(new_guide) 
        return new_guide
    
    def set_guides_description(self):
        guides_h,guides_v = self.get_guides()
        for val,g in guides_h:
            g.label = "hor {}".format(round(val,2))
        for val,g in guides_v:
            g.label = "vert {}".format(round(val,2))
            
    def remove_guides_description(self):
        guides_h,guides_v = self.get_guides()
        for val,g in guides_h:
            g.label = ""
        for val,g in guides_v:
            g.label = ""
       

    
    
    ### FOR TESTING
    
    
    def draw_line(self, points, width=.4, name="XaverTest", color="#000000", use_cur_layer=False):    

        if not use_cur_layer:
            parent = inkex.Layer.new(name)
            self.svg.add(parent)
        else:
            parent = self.svg.get_current_layer()

        elem = parent.add(inkex.PathElement())
        elem.style = {"stroke": "#000000", "stroke-width": str(width), "fill": "none"}
        elem.set("inkscape:label", name)
        
        move = Move(*points[0])
        lines = []
        
        for i in range(len(points)-1):
            lines.append(Line(*points[i+1]))

        elem.path = [move, *lines]
        
    def test_line(self):
        guides_h,guides_v = self.get_guides() 
        points = list(zip(guides_v,guides_h))
        self.draw_line(points,name="xt")
        
    def examine(self):
        
        guides_h,guides_v = self.get_guides()  
        
        
        parent = self.svg.get_current_layer()     
        
        ids = self.svg.get_ids()
        
        idpaths = [i for i in ids if "path" in i]
        
        hori = []
        verti = []
        elsi = []
        unnormi = []
        
        for nr,i in enumerate(idpaths):
            p =  self.svg.getElementById(i) 
            
            try: 
                p2 = p.path.to_superpath()
                p2 = p.path.to_non_shorthand()
                p2 = p.path.to_relative()
                
                if len(p2) > 2:
                    unnormi.append(p)
                else:
                    a = hasattr(p2[1], "dx")
                    b = hasattr(p2[1], "dy")
                    v1 = p2[1]
                    if b:
                        hori.append(p)
                    elif a:
                        verti.append(p)
                    else:
                        elsi.append(p)
            except:
                d = tb()
                pd()
                return
        
        def move_to_layer(name,paths):
            parent = inkex.Layer.new(name)
            self.svg.add(parent)
        
        
            for h in paths:
                old_parent = h.getparent()
                old_parent.remove(h)
                parent.append(h)
        
        
        move_to_layer("hori", hori)
        move_to_layer("verti", verti)
        move_to_layer("elsi", elsi)
        move_to_layer("unnormi", unnormi)

        

if __name__ == '__main__':
    XTools().run()
