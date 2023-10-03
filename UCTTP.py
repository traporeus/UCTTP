import xml.etree.ElementTree as ET
from ortools.sat.python import cp_model
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random
import itertools
from time import time as timer
import os



class TimetablingProblem():
    def __init__(self):
        self.data = None
        self.file_path = None
        self.type = None

    def read_data(self, file_path, data_type='unitime'):
        self.file_path = file_path
        self.data_type = data_type
        if data_type == 'unitime':
            self.data = self.read_unitime_data()
        elif data_type == 'itc19':
            self.data = self.read_itc19_data()
        return self.data

    def read_unitime_data(self):
        current_directory = os.getcwd()
        relative_path = os.path.join(current_directory, self.file_path)
        tree = ET.parse(relative_path)
        root = tree.getroot()
        data = {}

        file_name = os.path.splitext(os.path.basename(self.file_path))[0]
        data['name'] = file_name
        problem = root.attrib
        data['problem'] = problem

        rooms = []
        rooms_dict = {}
        for room in root.findall('rooms/room'):
            rooms_dict[room.attrib['id']] = room.attrib

            room_sharing = room.find('sharing')
            if room_sharing is not None:
                pattern_unit = room_sharing.find('pattern').attrib['unit']
                pattern = room_sharing.find('pattern').text
                freeForAll = room_sharing.find('freeForAll').attrib['value']
                notAvailable = room_sharing.find('notAvailable').attrib['value']
                departments = []
                for dm in room_sharing.findall('department'):
                    departments.append(dm.attrib)
                rooms_dict[room.attrib['id']]['sharing'] = {'pattern_unit':pattern_unit,'pattern': pattern, 'freeForAll': freeForAll, 'notAvailable': notAvailable, 'departments': departments}
            else:
                rooms_dict[room.attrib['id']]['sharing'] = None
            rooms.append(room.attrib) #adds the updated room.attrib to the list of rooms
        data['rooms'] = rooms_dict
        class_dict = {}
        instructors = []
        classes = []
        for class_ in root.findall('classes/class'):
            class_instructors_find = class_.findall('instructor')
            class_instructors = [instructor.attrib for instructor in class_instructors_find]

            instructors.extend([instructor['id'] for instructor in class_instructors])
            instructors = list(set(instructors))

            class_rooms_find = class_.findall('room')
            class_rooms = [room.attrib for room in class_rooms_find]
            class_rooms_id = [room['id'] for room in class_rooms]

            class_dates = class_.attrib['dates']
            class_time = class_.findall('time')
            class_time = [time.attrib for time in class_time]
            class_time_list = [(days,start,lenght,class_dates) for days,start,lenght in zip([time['days'] for time in class_time],[time['start'] for time in class_time],[time['length'] for time in class_time])]

            
            class_dict[class_.attrib['id']] = class_.attrib
            class_dict[class_.attrib['id']]['instructors'] = class_instructors
            class_dict[class_.attrib['id']]['rooms'] = class_rooms
            class_dict[class_.attrib['id']]['room_list'] = class_rooms_id
            class_dict[class_.attrib['id']]['time'] = class_time
            class_dict[class_.attrib['id']]['time_list'] = class_time_list
            classes.append(class_.attrib) #adds the updated class.attrib to the list of classes

        data['classes'] = class_dict
        data['instructors'] = instructors
        self.class_count_nc = len([class_ for class_ in data['classes'].values() if class_['committed'] == 'false']) #number of non-committed classes

        group_constraints_dict = {}
        group_constraints = []
        for group_constraint in root.findall('groupConstraints/constraint'):
            group_constraints_dict[group_constraint.attrib['id']] = group_constraint.attrib

            constraint_classes = []
            for class_ in group_constraint.findall('class'):
                constraint_classes.append(class_.attrib)

            group_constraints_dict[group_constraint.attrib['id']]['classes'] = constraint_classes
            group_constraints.append(group_constraint.attrib)

        data['constraints'] = group_constraints

        student_dict = {}
        for student in root.findall('students/student'):
            student_dict[student.attrib['id']] = student.attrib

            student_offering = [offering.attrib for offering in student.findall('offering')]
            student_dict[student.attrib['id']]['offering'] = student_offering

            student_classes = [class_.attrib['id'] for class_ in student.findall('class')]
            student_dict[student.attrib['id']]['classes'] = student_classes        
            
            student_prohibited_classes = [class_.attrib['id'] for class_ in student.findall('prohibited-class')]

            student_dict[student.attrib['id']]['prohibited-classes'] = student_prohibited_classes
        data['students'] = student_dict
        return data
        
    def read_itc19_data(self):
        tree = ET.parse(self.file_path)
        root = tree.getroot()
        data = {}

        problem = root.attrib
        data['problem'] = problem
        
        rooms_dict = {}
        travel_times = {}
        for room in root.findall('rooms/room'):
            rooms_dict[room.attrib['id']] = room.attrib

            times = room.findall('travel')
            for time in times:
                travel_times[(room.attrib['id'], time.attrib['room'])] = time.attrib['value']
                travel_times[(time.attrib['room'], room.attrib['id'])] = time.attrib['value']      

            unavailable = room.findall('unavailable')
            rooms_dict[room.attrib['id']]['unavailable'] = [un.attrib for un in unavailable]
        data['rooms'] = rooms_dict
        data['travel_times'] = travel_times

        course_dict = {}
        classes = []
        for course in root.findall('courses/course'):
            course_id = course.attrib['id']
            course_dict[course_id] = {}
            for config in course.findall('config'):
                config_id = config.attrib['id']
                course_dict[course_id][config_id] = {}
                for subpart in config.findall('subpart'):
                    subpart_id = subpart.attrib['id']
                    course_dict[course_id][config_id][subpart_id] = {}
                    for class_ in subpart.findall('class'):
                        class_id = class_.attrib['id']
                        course_dict[course_id][config_id][subpart_id][class_id] = class_.attrib
                        rooms = class_.findall('room')
                        times = class_.findall('time')
                        course_dict[course_id][config_id][subpart_id][class_id]['rooms'] = [room.attrib for room in rooms]
                        course_dict[course_id][config_id][subpart_id][class_id]['times'] = [time.attrib for time in times]
                        class_dict = class_.attrib
                        class_dict['rooms'] = [room.attrib for room in rooms]
                        class_dict['room_ids'] = [room.attrib['id'] for room in rooms]
                        if len(class_dict['rooms']) == 0:
                            class_dict['rooms'] = [{'id':'-'+class_id,"penalty":"0"}]
                            class_dict['room_ids'] = ['-'+class_id]
                        class_dict['times'] = []
                        class_dict['time_tuples'] = []
                        for time in times:
                            time_dict = time.attrib
                            time_tuple = (int(time_dict['start']), int(time_dict['length']),time_dict['days'],time_dict['weeks'])
                            time_dict['time_tuple'] = time_tuple
                            class_dict['time_tuples'].append(time_tuple)
                            class_dict['times'].append(time_dict)
                        class_dict['course'] = course.attrib['id']
                        class_dict['config'] = config.attrib['id']
                        class_dict['subpart'] = subpart.attrib['id']
                        classes.append(class_dict)

        data['courses'] = course_dict
        data['classes'] = classes

        student_dict = {}
        for student in root.findall('students/student'):
            student_dict[student.attrib['id']] = student.attrib
            student_dict[student.attrib['id']]['courses'] = [course.attrib['id'] for course in student.findall('course')]
        data['students'] = student_dict

        constraints = []
        for constraint in root.findall('distributions/distribution'):
            distribution = constraint.attrib
            distribution['classes'] = [class_.attrib for class_ in constraint.findall('class')]
            constraints.append(distribution)
        data['constraints'] = constraints
        return data

    def time_overlap(self, t, t_bar):
        if any(x == y == '1' for x, y in zip(t[3], t_bar[3])):
            if any(x == y == '1' for x, y in zip(t[0], t_bar[0])):
                if int(t_bar[1]) < int(t[1]) + int(t[2]) and int(t[1]) <  int(t_bar[1]) + int(t_bar[2]):
                        return True
        return False

    def student_traveltime_overlap(self, r, r_bar):
        #higher than 670 meters
        room1 = self.rooms[r].get('location',None)
        room2 = self.rooms[r_bar].get('location',None)
        if room1 is None or room2 is None:
            return True
        room1_1,room1_2 = room1.split(',')
        room2_1,room2_2 = room2.split(',')
        distance = 10*np.sqrt((int(room1_1)-int(room2_1))**2 + (int(room1_2)-int(room2_2))**2)
        if distance > 670:
            return True
        return False   

    def adjacent_time_segments(self, t, t_bar):
        days1 = [i for i, x in enumerate(t[0]) if x == "1"]
        days2 = [i for i, x in enumerate(t_bar[0]) if x == "1"]
        if days1==days2:
            if int(t_bar[1]) == int(t[1]) + int(t[2]):
                return True
            if int(t[1]) == int(t_bar[1]) + int(t_bar[2]):
                return True
        return False

    def NHB_GTE(self,t,t_bar):
        #at least 1 hour between classes
        if int(t[1]) == int(t_bar[1]):
            return False
        if int(t[1]) < int(t_bar[1]) and int(t[1]) + int(t[2]) + 12 <= int(t_bar[1]):
            return True
        if int(t_bar[1]) < int(t[1]) and int(t_bar[1]) + int(t_bar[2]) + 12 <= int(t[1]):
            return True
        return False

    def add_edge(self,conflict_graph,var1, var2):
        if var1 not in conflict_graph:
            conflict_graph[var1] = []
        if var2 not in conflict_graph:
            conflict_graph[var2] = []
        
        # Check if the edge already exists
        if var2 not in conflict_graph[var1]:
            conflict_graph[var1].append(var2)
        
        if var1 not in conflict_graph[var2]:
            conflict_graph[var2].append(var1)

    def create_unitime_model(self):
        self.model = cp_model.CpModel()

        problem = self.data['problem']

        nrDays = int(problem['nrDays'])
        slotsPerDay = int(problem['slotsPerDay'])
        nrWeeks = 8

        self.time_slots = [time_slot for time_slot in range(slotsPerDay)]
        days = [day for day in range(nrDays)]
        weeks = [week for week in range(nrWeeks)]

        self.classes = self.data['classes']
        self.rooms = self.data['rooms']
        self.rooms['dummy'] = {'id':'dummy','constraint':'false','pref':'0'}
        self.students  = self.data['students']
        class_ids = [class_ for class_ in self.classes.keys()]
        room_ids = [room for room in self.rooms.keys()]
        self.class_variables = {}
        self.conflict_graph = set()

        for class_ in self.classes.values():
            if len(class_['room_list']) == 0:
                class_['room_list'] = ['dummy']
            for time in class_['time_list']:
                for room in class_['room_list']:
                    self.class_variables[(class_['id'], time, room)] = self.model.NewBoolVar(f"class_{class_['id']}_time_{time}_room_{room}")
        
        for i,class_ in enumerate(self.classes.values()): #only one room per class
            ctr = [(class_['id'],time,room) for time in class_['time_list'] for room in class_['room_list']]
            pairs = list(itertools.combinations(ctr, 2))
            all_var = [self.class_variables[var] for var in ctr]
            self.model.AddExactlyOne(all_var)
            for var1, var2 in pairs:
                # Add edges to the conflict graph as tuples
                edge = (var1, var2)
                edge_mirrored = (var2, var1)
                if edge_mirrored not in self.conflict_graph:
                    self.conflict_graph.add(edge)

                    

        #no overlapping classes can share rooms
        #print('starting...')
        class_pairs = list(itertools.combinations(self.classes.values(), 2))
        can_share_room = []
        #get lists of allowable room sharing
        for constraint in self.data['constraints']:
            if constraint['type'] == 'CAN_SHARE_ROOM':
                list_of_rooms = [rid['id'] for rid in constraint['classes']]
                can_share_room.append(list_of_rooms)
            elif constraint['type'] == 'MEET_WITH':
                list_of_rooms = [rid['id'] for rid in constraint['classes']]
                can_share_room.append(list_of_rooms)
        count = 0
        for class_, class_bar in class_pairs:
            allowed_sharing = False
            for listi_room in can_share_room:
                if class_['id'] in listi_room and class_bar['id'] in listi_room:
                    allowed_sharing = True
            if not allowed_sharing:
                for room in class_['room_list']:
                    for room_bar in class_bar['room_list']:
                        if room == room_bar and self.rooms[room]['constraint'] != 'false':
                            for time in class_['time_list']:
                                for time_bar in class_bar['time_list']:
                                    if self.time_overlap(time, time_bar):
                                        var1 = (class_['id'], time, room)
                                        var2 = (class_bar['id'], time_bar, room_bar)
                                        count += 1
                                        self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                        edge = (var1, var2)
                                        edge_mirrored = (var2, var1)
                                        if edge_mirrored not in self.conflict_graph:
                                            self.conflict_graph.add(edge)
        # print(count)
        # print('Group constraints...')
        # #group constraints
        count = 0
        travel_count = 0
        count_types = {}
        for constraint in self.data['constraints']:
            if count_types.get(constraint['type']) == None: 
                count_types[constraint['type']] = {'hard':0,'soft':0,'total':0}
            count_types[constraint['type']]['total'] += 1
            if constraint['pref'] != 'R':
                count_types[constraint['type']]['soft'] += 1
            if constraint['pref'] == 'R':
                count_types[constraint['type']]['hard'] += 1
                count += 1
                if constraint['type'] == 'DIFF_TIME':
                    class_pairs = list(itertools.combinations(constraint['classes'], 2))
                    for class_, class_bar in class_pairs:
                        for time in self.classes[class_['id']]['time_list']:
                            for time_bar in self.classes[class_bar['id']]['time_list']:
                                if self.time_overlap(time, time_bar):
                                    for room in self.classes[class_['id']]['room_list']:
                                        for room_bar in self.classes[class_bar['id']]['room_list']:
                                            if room != room_bar: #to avoid duplicate constraints
                                                var1 = (class_['id'], time, room)
                                                var2 = (class_bar['id'], time_bar, room_bar)
                                                count += 1
                                                self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                                edge = (var1, var2)
                                                edge_mirrored = (var2, var1)
                                                if edge_mirrored not in self.conflict_graph:
                                                    self.conflict_graph.add(edge)
                elif constraint['type'] == 'SAME_ROOM':
                    class_pairs = list(itertools.combinations(constraint['classes'], 2))
                    for class_, class_bar in class_pairs:
                        for time in self.classes[class_['id']]['time_list']:
                            for time_bar in self.classes[class_bar['id']]['time_list']:
                                    for room in self.classes[class_['id']]['room_list']:
                                        for room_bar in self.classes[class_bar['id']]['room_list']:
                                            if room != room_bar: #to avoid duplicate constraints
                                                var1 = (class_['id'], time, room)
                                                var2 = (class_bar['id'], time_bar, room_bar)
                                                count += 1
                                                self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                                edge = (var1, var2)
                                                edge_mirrored = (var2, var1)
                                                if edge_mirrored not in self.conflict_graph:
                                                    self.conflict_graph.add(edge)
                elif constraint['type'] == 'MEET_WITH': 
                    class_pairs = list(itertools.combinations(constraint['classes'], 2))
                    for class_, class_bar in class_pairs:
                        for time in self.classes[class_['id']]['time_list']:
                            for time_bar in self.classes[class_bar['id']]['time_list']:
                                    for room in self.classes[class_['id']]['room_list']:
                                        for room_bar in self.classes[class_bar['id']]['room_list']:
                                            if room != room_bar: #to avoid duplicate constraints
                                                var1 = (class_['id'], time, room)
                                                var2 = (class_bar['id'], time_bar, room_bar)
                                                count += 1
                                                self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                                edge = (var1, var2)
                                                edge_mirrored = (var2, var1)
                                                if edge_mirrored not in self.conflict_graph:
                                                    self.conflict_graph.add(edge)
                    for class_, class_bar in class_pairs:
                        if self.classes[class_['id']]['time_list'][0][2] == self.classes[class_bar['id']]['time_list'][0][2]:
                            for time in self.classes[class_['id']]['time_list']:
                                for time_bar in self.classes[class_bar['id']]['time_list']:
                                    if int(time[1]) not in [i for i in range(int(time_bar[1])-5, int(time_bar[1])+6)]:
                                        for room in self.classes[class_['id']]['room_list']:
                                            for room_bar in self.classes[class_bar['id']]['room_list']:
                                                var1 = (class_['id'], time, room)
                                                var2 = (class_bar['id'], time_bar, room_bar)
                                                count += 1
                                                self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                                edge = (var1, var2)
                                                edge_mirrored = (var2, var1)
                                                if edge_mirrored not in self.conflict_graph:
                                                    self.conflict_graph.add(edge)
                        else:
                            short = np.argmin([int(self.classes[class_['id']]['time_list'][0][2]), int(self.classes[class_bar['id']]['time_list'][0][2])])
                            c = [class_, class_bar]
                            for time in self.classes[c[short]['id']]['time_list']:
                                for time_bar in self.classes[c[short-1]['id']]['time_list']:
                                    if int(time[1]) >= int(time_bar[1]) and int(time[1])+int(time[2]) <= int(time_bar[1])+int(time_bar[2]):
                                        for room in self.classes[c[short]['id']]['room_list']:
                                            for room_bar in self.classes[c[short-1]['id']]['room_list']:
                                                var1 = (c[short]['id'], time, room)
                                                var2 = (c[short-1]['id'], time_bar, room_bar)
                                                count += 1
                                                self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                                edge = (var1, var2)
                                                edge_mirrored = (var2, var1)
                                                if edge_mirrored not in self.conflict_graph:
                                                    self.conflict_graph.add(edge)
                    for class_, class_bar in class_pairs:
                        for time in self.classes[class_['id']]['time_list']:
                            for time_bar in self.classes[class_bar['id']]['time_list']:
                                days1 = [i for i, x in enumerate(time[0]) if x == "1"]
                                days2 = [i for i, x in enumerate(time_bar[0]) if x == "1"]
                                days1_set = set(days1)
                                days2_set = set(days2)
                                is_contained = days1_set.issubset(days2_set) or days2_set.issubset(days1_set)
                                if is_contained == False:
                                    for room in self.classes[class_['id']]['room_list']:
                                        for room_bar in self.classes[class_bar['id']]['room_list']:
                                            var1 = (class_['id'], time, room)
                                            var2 = (class_bar['id'], time_bar, room_bar)
                                            count += 1
                                            self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                            edge = (var1, var2)
                                            edge_mirrored = (var2, var1)
                                            if edge_mirrored not in self.conflict_graph:
                                                self.conflict_graph.add(edge)
                elif constraint['type'] == 'SAME_TIME' or constraint['type'] == 'SAME_START': #SAME_START is a special case of SAME_TIME
                    class_pairs = list(itertools.combinations(constraint['classes'], 2))
                    for class_, class_bar in class_pairs:
                        if self.classes[class_['id']]['time_list'][0][2] == self.classes[class_bar['id']]['time_list'][0][2] or constraint['type'] == 'SAME_START':
                            for time in self.classes[class_['id']]['time_list']:
                                for time_bar in self.classes[class_bar['id']]['time_list']:
                                    if int(time[1]) not in [i for i in range(int(time_bar[1])-5, int(time_bar[1])+6)]:
                                        for room in self.classes[class_['id']]['room_list']:
                                            for room_bar in self.classes[class_bar['id']]['room_list']:
                                                var1 = (class_['id'], time, room)
                                                var2 = (class_bar['id'], time_bar, room_bar)
                                                count += 1
                                                self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                                edge = (var1, var2)
                                                edge_mirrored = (var2, var1)
                                                if edge_mirrored not in self.conflict_graph:
                                                    self.conflict_graph.add(edge)
                        else:
                            short = np.argmin([int(self.classes[class_['id']]['time_list'][0][2]), int(self.classes[class_bar['id']]['time_list'][0][2])])
                            c = [class_, class_bar]
                            for time in self.classes[c[short]['id']]['time_list']:
                                for time_bar in self.classes[c[short-1]['id']]['time_list']:
                                    if int(time[1]) >= int(time_bar[1]) and int(time[1])+int(time[2]) <= int(time_bar[1])+int(time_bar[2]):
                                        for room in self.classes[c[short]['id']]['room_list']:
                                            for room_bar in self.classes[c[short-1]['id']]['room_list']:
                                                var1 = (c[short]['id'], time, room)
                                                var2 = (c[short-1]['id'], time_bar, room_bar)
                                                count += 1
                                                self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                                edge = (var1, var2)
                                                edge_mirrored = (var2, var1)
                                                if edge_mirrored not in self.conflict_graph:
                                                    self.conflict_graph.add(edge)
                elif constraint['type'] == 'SAME_DAYS':
                    class_pairs = list(itertools.combinations(constraint['classes'], 2))
                    for class_, class_bar in class_pairs:
                        for time in self.classes[class_['id']]['time_list']:
                            for time_bar in self.classes[class_bar['id']]['time_list']:
                                days1 = [i for i, x in enumerate(time[0]) if x == "1"]
                                days2 = [i for i, x in enumerate(time_bar[0]) if x == "1"]
                                days1_set = set(days1)
                                days2_set = set(days2)
                                is_contained = days1_set.issubset(days2_set) or days2_set.issubset(days1_set)
                                if is_contained == False:
                                    for room in self.classes[class_['id']]['room_list']:
                                        for room_bar in self.classes[class_bar['id']]['room_list']:
                                            var1 = (class_['id'], time, room)
                                            var2 = (class_bar['id'], time_bar, room_bar)
                                            count += 1
                                            self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                            edge = (var1, var2)
                                            edge_mirrored = (var2, var1)
                                            if edge_mirrored not in self.conflict_graph:
                                                self.conflict_graph.add(edge)
                elif constraint['type'] == 'BTB_TIME': #back-to-back classes (implies same days)
                    class_pairs = list(itertools.combinations(constraint['classes'], 2))
                    for class_, class_bar in class_pairs:
                        for time in self.classes[class_['id']]['time_list']:
                            for time_bar in self.classes[class_bar['id']]['time_list']:
                                if self.adjacent_time_segments(time, time_bar) == False:
                                    for room in self.classes[class_['id']]['room_list']:
                                        for room_bar in self.classes[class_bar['id']]['room_list']:
                                            var1 = (class_['id'], time, room)
                                            var2 = (class_bar['id'], time_bar, room_bar)
                                            count += 1
                                            self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                            edge = (var1, var2)
                                            edge_mirrored = (var2, var1)
                                            if edge_mirrored not in self.conflict_graph:
                                                self.conflict_graph.add(edge)
                elif constraint['type'] == 'NHB_GTE(1)': #at least one hour between classes
                    class_pairs = list(itertools.combinations(constraint['classes'], 2))
                    for class_, class_bar in class_pairs:
                        for time in self.classes[class_['id']]['time_list']:
                            for time_bar in self.classes[class_bar['id']]['time_list']:
                                days1 = [i for i, x in enumerate(time[0]) if x == "1"]
                                days2 = [i for i, x in enumerate(time_bar[0]) if x == "1"]
                                if days1==days2:
                                    if self.NHB_GTE(time, time_bar) == False:
                                        for room in self.classes[class_['id']]['room_list']:
                                            for room_bar in self.classes[class_bar['id']]['room_list']:
                                                var1 = (class_['id'], time, room)
                                                var2 = (class_bar['id'], time_bar, room_bar)
                                                count += 1
                                                self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                                edge = (var1, var2)
                                                edge_mirrored = (var2, var1)
                                                if edge_mirrored not in self.conflict_graph:
                                                    self.conflict_graph.add(edge)
                elif constraint['type'] == 'SAME_STUDENTS':
                    class_pairs = list(itertools.combinations(constraint['classes'], 2))
                    for class_, class_bar in class_pairs:
                        for time in self.classes[class_['id']]['time_list']:
                            for time_bar in self.classes[class_bar['id']]['time_list']:
                                if self.time_overlap(time, time_bar):
                                    for room in self.classes[class_['id']]['room_list']:
                                        for room_bar in self.classes[class_bar['id']]['room_list']:
                                            travel_count += 1
                                            var1 = (class_['id'], time, room)
                                            var2 = (class_bar['id'], time_bar, room_bar)
                                            count += 1
                                            self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                            edge = (var1, var2)
                                            edge_mirrored = (var2, var1)
                                            if edge_mirrored not in self.conflict_graph:
                                                self.conflict_graph.add(edge)
                                elif self.adjacent_time_segments(time, time_bar):
                                    for room in self.classes[class_['id']]['room_list']:
                                        for room_bar in self.classes[class_bar['id']]['room_list']:
                                            if self.student_traveltime_overlap(room, room_bar):
                                                var1 = (class_['id'], time, room)
                                                var2 = (class_bar['id'], time_bar, room_bar)
                                                count += 1
                                                self.model.AddImplication(self.class_variables[var1], self.class_variables[var2].Not())
                                                edge = (var1, var2)
                                                edge_mirrored = (var2, var1)
                                                if edge_mirrored not in self.conflict_graph:
                                                    self.conflict_graph.add(edge)
                                                travel_count += 1


        # print(travel_count)
        # print(count_types)
        # print(count)

    def solve(self):
        #print("now solving...")
        #solve the self.model
        self.solver = cp_model.CpSolver()
        self.solver.parameters.log_search_progress = False
        self.solver.parameters.fill_tightened_domains_in_response = True
        self.solver.parameters.num_search_workers = 8


        seed = 97
        self.solver.parameters.random_seed = seed
        self.solver.parameters.max_time_in_seconds = 460.0
        status = self.solver.Solve(self.model)
        self.tightened_vars = self.solver.ResponseProto().tightened_variables

        print("status: ", self.solver.StatusName(status))
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            #obj, cost,spread = self.get_objective()
            #print("objective: ", obj,'spread:',spread)
            return self.solver.StatusName(status)
        return self.solver.StatusName(status)

    def find_fixed_variables(self):
        try:
            self.tightened_vars
        except:
            self.solve()
        self.fixed_vars = []
        for class_, time, room in self.class_variables:
            dom = self.tightened_vars[self.class_variables[(class_, time, room)].Index()].domain
            if dom == [0,0] or dom == [1,1]:
                self.fixed_vars.append((class_, time, room))

    def get_objective(self, solution=None):
        if solution == None:
            solution = self.save_solution()
        costs = 0
        spread_costs = 0
        costs_dict = {c:0 for c in solution.keys()}
        for constraint in self.data['constraints']:
            if constraint['type'] == 'SPREAD':
                spread_list = constraint['classes']
                costs += self.check_spread(solution, costs_dict, spread_list)
                spread_costs += self.check_spread(solution, costs_dict, spread_list)
            elif constraint['pref'] != 'R' and constraint['pref'] != 'P':
                if constraint['type'] == 'SAME_ROOM':
                    costs += self.check_same_room(solution, costs_dict, constraint['classes'], constraint['pref'])
                elif constraint['type'] == 'BTB_TIME':
                    costs += self.check_btb_time(solution, costs_dict, constraint['classes'], constraint['pref'])
                elif constraint['type'] == 'DIFF_TIME':
                    costs += self.check_diff_time(solution, costs_dict, constraint['classes'], constraint['pref']) 
                elif constraint['type'] == 'NHB_GTE(1)':
                    costs += self.check_nhb_gte(solution, costs_dict, constraint['classes'], constraint['pref']) 
                elif constraint['type'] == 'SAME_DAYS':
                    costs += self.check_same_days(solution, costs_dict, constraint['classes'], constraint['pref']) 
        for class_,(time,room) in solution.items():
            costs += self.room_costs(class_,room,costs_dict)
            costs += self.time_costs(class_,time,costs_dict)
        return costs, costs_dict, spread_costs

    def room_costs(self,class_,room, costs_dict):
        for room_bar in self.classes[class_]['rooms']:
            if room_bar['id'] == room:
                cost = int(float(room_bar['pref']))
                costs_dict[class_] += cost
                return cost
        return 0

    def time_costs(self,class_,time,costs_dict):
        for time_bar in self.classes[class_]['time']:
            if time_bar['days'] == time[0] and time_bar['start'] == time[1]:
                cost = int(float(time_bar['pref']))
                costs_dict[class_] += cost
                return cost

    def check_spread(self, sol, costs_dict, spread_list):
        class_pairs = list(itertools.combinations(spread_list, 2))
        costs = 0
        for class_pair in class_pairs:
            class_ = class_pair[0]['id']
            class_bar = class_pair[1]['id']
            sol1 = sol.get(class_,None)
            sol2 = sol.get(class_bar,None)
            if sol1 == None or sol2 == None:
                continue
            if self.time_overlap(sol1[0], sol2[0]):
                costs_dict[class_] += 1
                costs_dict[class_bar] += 1
                costs += 1
        return costs

    def check_same_room(self, sol, costs_dict, same_room_list, pref):
        class_pairs = list(itertools.combinations(same_room_list, 2))
        costs = 0
        satisfied = True
        for class_pair in class_pairs:
            class_ = class_pair[0]['id']
            class_bar = class_pair[1]['id']
            sol1 = sol.get(class_,None)
            sol2 = sol.get(class_bar,None)
            if sol1 == None or sol2 == None:
                continue
            if sol1[1] == sol2[1]:
                costs_dict[class_] += int(pref)
                costs_dict[class_bar] += int(pref)
                costs += int(pref)
            else: 
                satisfied = False
        if not satisfied:
            return 0
        return costs

    def check_btb_time(self, sol, costs_dict, btb_time_list, pref):
        class_pairs = list(itertools.combinations(btb_time_list, 2))
        costs = 0
        satisfied = True
        for class_pair in class_pairs:
            class_ = class_pair[0]['id']
            class_bar = class_pair[1]['id']
            sol1 = sol.get(class_,None)
            sol2 = sol.get(class_bar,None)
            if sol1 == None or sol2 == None:
                continue
            if self.adjacent_time_segments(sol1[0], sol2[0]):
                costs_dict[class_] += int(pref)
                costs_dict[class_bar] += int(pref)
                costs += int(pref)
            else:
                satisfied = False
        if not satisfied:
            return 0
        return costs

    def check_diff_time(self, sol, costs_dict, diff_time_list, pref):
        class_pairs = list(itertools.combinations(diff_time_list, 2))
        costs = 0
        satisfied = True
        for class_pair in class_pairs:
            class_ = class_pair[0]['id']
            class_bar = class_pair[1]['id']
            sol1 = sol.get(class_,None)
            sol2 = sol.get(class_bar,None)
            if sol1 == None or sol2 == None:
                continue
            if self.time_overlap(sol1[0], sol2[0]) == False:
                costs_dict[class_] += int(pref)
                costs_dict[class_bar] += int(pref)
                costs += int(pref)
            else:
                satisfied = False
        if not satisfied:
            return 0
        return costs

    def check_nhb_gte(self, sol, costs_dict, nhb_gte_list, pref):
        class_pairs = list(itertools.combinations(nhb_gte_list, 2))
        costs = 0
        satisfied = True
        for class_pair in class_pairs:
            class_ = class_pair[0]['id']
            class_bar = class_pair[1]['id']
            sol1 = sol.get(class_,None)
            sol2 = sol.get(class_bar,None)
            if sol1 == None or sol2 == None:
                continue
            if self.NHB_GTE(sol1[0], sol2[0]):
                costs_dict[class_] += int(pref)
                costs_dict[class_bar] += int(pref)
                costs += int(pref)
            else:
                satisfied = False
        if not satisfied:
            return 0
        return costs
    
    def check_same_days(self, sol, costs_dict, same_days_list, pref):
        class_pairs = list(itertools.combinations(same_days_list, 2))
        costs = 0
        satisfied = True
        for class_pair in class_pairs:
            class_ = class_pair[0]['id']
            class_bar = class_pair[1]['id']
            sol1 = sol.get(class_,None)
            sol2 = sol.get(class_bar,None)
            if sol1 == None or sol2 == None:
                continue
            days1 = [i for i, x in enumerate(sol1[0][0]) if x == "1"]
            days2 = [i for i, x in enumerate(sol2[0][0]) if x == "1"]
            days1_set = set(days1)
            days2_set = set(days2)
            is_contained = days1_set.issubset(days2_set) or days2_set.issubset(days1_set)
            if is_contained:
                costs_dict[class_] += int(pref)
                costs_dict[class_bar] += int(pref)
                costs += int(pref)
            else:
                satisfied = False
        if not satisfied:
            return 0
        return costs

    def check_feasibility_partial_sol(self, solution):
        time_start = timer()
        #print('checking feasibility...')
        self.solver = cp_model.CpSolver()
        # Create a new model
        self.temp_model = cp_model.CpModel()
        self.temp_model.CopyFrom(self.model)
        

        # Set the variable values from the solution
        for i,sol in enumerate(solution.items()):
            variable = sol[0]
            value = sol[1]

            self.temp_model.AddBoolAnd(self.class_variables[variable,tuple(value[0]),value[1]])
        
        status = self.solver.Solve(self.temp_model)

        # Check the status of the solver
        if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
            #print(f'Number of solutions: {len(solution_printer.solution_list)}')
            #print(f'Best obj: {min(solution_printer.solution_list)}')
            #print(f"The provided solution is {self.solver.StatusName(status)}.")
            #print(f"Objective value: {self.check_objective()}")
            return True
        else:
            #print("The provided solution is infeasible.")
            return False

    def check_feasibility_full_sol(self,solution):
        time_start = timer()
        sol_ctr = [(c,v[0],v[1]) for c,v in solution.items()]
        sol_pairs = itertools.combinations(sol_ctr,2)
        for sol1, sol2 in sol_pairs:
            if (sol1,sol2) in self.conflict_graph or (sol2,sol1) in self.conflict_graph:
                return False
        return True

    def timetable_from_solution(self):
        # Extract variable assignments
        class_assignments = {}
        for class_, time, room in self.class_variables:
            if self.solver.BooleanValue(self.class_variables[(class_, time, room)]):
                class_assignments[class_] = (time, room)
        
        # Define the schedule data
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Satudray", "Sunday"]

        # Create an empty schedule grid
        schedule = [["-" for _ in range(len(weekdays))] for _ in range(len(self.time_slots))]
        # Fill in the schedule with class information
        for class_, assignments in class_assignments.items():
            time, room = assignments
            days = [i for i, x in enumerate(time[0]) if x == "1"]
            for day in days:
                for slot in range(int(time[1]), int(time[1])+int(time[2])):
                    if schedule[slot][day] == "-":
                        schedule[slot][day] = f"Class {class_} - Room {room}"
                    else:
                        schedule[slot][day] += f"\nClass {class_} - Room {room}"
        pandas_schedule = pd.DataFrame(schedule, index=self.time_slots, columns=weekdays)
        pandas_schedule.to_csv('schedule.csv')
    
    def save_solution(self):
        # Extract variable assignments
        class_assignments = {}
        for class_, time, room in self.class_variables:
            if self.solver.BooleanValue(self.class_variables[(class_, time, room)]):
                class_assignments[class_] = (time, room)

        # with open('solution.json', 'w') as f:
        #     json.dump(class_assignments, f)
        return class_assignments

    def sort_dict_by_value(self,dict):
        # Create a list of tuples, where each tuple contains the key and the value of the dictionary.
        sorted_list = [(key, value) for key, value in dict.items()]

        # Sort the list by the values.
        sorted_list.sort(key=lambda x: x[1])

        keys = [x[0] for x in sorted_list]
        # Return the (only keys) sorted list.
        return keys

    def create_department_table(self,list_of_paths):
        #create a list of all the department tables
        department_table = pd.DataFrame(columns=['Department', '#Classes','#nc-Classes','#Rooms','#Constraints'])
        for path in list_of_paths:
            department = self.read_data(path, data_type='unitime')
            class_count= len([class_ for class_ in department['classes'].values()])
            class_count_nc = len([class_ for class_ in department['classes'].values() if class_['committed'] == 'false'])
            room_count = len(department['rooms'])
            constraint_count = len(department['constraints'])
            department_table = department_table.append({'Department':department['name'],'#Classes':class_count,'#nc-Classes':class_count_nc,'#Rooms':room_count,'#Constraints': constraint_count},ignore_index=True)
        return department_table

    def large_neighborhood_search(self, solution=None):
        if solution == None:
            solution = self.solution
        # Initialize the current and best solutions
        self.find_fixed_variables()
        best_sol = solution.copy()
        best_sol_obj, best_sol_costs, best_cost_spread = self.get_objective(solution)
        cur_sol = solution.copy()
        cur_sol_obj, cur_sol_costs, cur_cost_spread = best_sol_obj, best_sol_costs, best_cost_spread

        temp_sol_objs = []
        cur_sol_objs = []
        best_sol_objs = []
        timestamps = []  # To store timestamps
        iterations = []  # To store iteration numbers

        repeat = True
        it = 0
        print('it - temp - cur - best')
        start_time = timer()
        while repeat:
            it += 1
            temp_sol = self.destroy(cur_sol)
            temp_sol = self.repair(temp_sol)
            temp_sol_obj, temp_sol_costs, temp_cost_spread = self.get_objective(temp_sol)

            # Collect data at each iteration
            timestamps.append(int(timer() - start_time))
            iterations.append(it)
            temp_sol_objs.append(temp_sol_obj)
            cur_sol_objs.append(cur_sol_obj)
            best_sol_objs.append(best_sol_obj)

            print(f'{it} - {temp_sol_obj} - {cur_sol_obj} - {best_sol_obj}')
            if temp_sol_obj < cur_sol_obj:
                cur_sol = temp_sol
                cur_sol_obj = temp_sol_obj
                cur_sol_costs = temp_sol_costs
                cur_cost_spread = temp_cost_spread
            if temp_sol_obj < best_sol_obj:
                best_sol = temp_sol
                best_sol_obj = temp_sol_obj
                best_sol_costs = temp_sol_costs
                best_cost_spread = temp_cost_spread
            if it == 500 or timer() - start_time > 1000:
                repeat = False
        print('Best obj: ', best_sol_obj)
        return best_sol_obj,best_sol_objs,cur_sol_objs,temp_sol_objs,timestamps,iterations

    def destroy(self, solution=None, size=0.3):
        #get a random subset of the solution
        if solution == None:
            solution = self.solution
        subset = {}
        for class_,val in solution.items():
            if (class_,val[0],val[1]) in self.fixed_vars:
                subset[class_] = solution[class_]
            if random.random() < 1-size:
                subset[class_] = solution[class_]
        return subset

    def repair(self,solution):
        self.solver = cp_model.CpSolver()
        # Create a new model
        temp_model = cp_model.CpModel()
        temp_model.CopyFrom(self.model)

        # Set the variable values from the solution
        for i,sol in enumerate(solution.items()):
            variable = sol[0]
            value = sol[1]

            temp_model.AddBoolAnd(self.class_variables[variable,tuple(value[0]),value[1]])

        self.solver.Solve(temp_model)
        return self.save_solution()

    def adaptive_neighborhood_search(self, solution=None, parameters=None):
        if solution == None:
            solution = self.solution
        # Initialize the current and best solutions
        self.find_fixed_variables()
        best_sol = solution.copy()
        best_sol_obj, best_sol_costs, best_cost_spread = self.get_objective(best_sol)
        cur_sol = solution.copy()
        cur_sol_obj, cur_sol_costs, cur_cost_spread = best_sol_obj, best_sol_costs, best_cost_spread

        temp_sol_objs = []
        cur_sol_objs = []
        best_sol_objs = []
        timestamps = []  # To store timestamps
        iterations = []  # To store iteration numbers
        d_ws = []

        destroy_methods = ['worst','random','room']
        destroy_weights = [100 for _ in range(len(destroy_methods))]
        repair_methods = ['standard']
        repair_weights = [100 for _ in range(len(repair_methods))]

        if parameters != None:
            decay = parameters['decay']     
            w1 = parameters['w1']
            w2 = parameters['w2']
            w3 = parameters['w3']
            size = parameters['size']
            p = parameters['p']
        else:
            decay = 0.50
            w1 = 50
            w2 = 30
            w3 = 10
            w4 = 1
            p = 0.8
            size = 0.3


        repeat = True
        it = 0
        print('it - temp - cur - best')
        start_time = timer()
        while repeat:
            it += 1
            accept = False
            better = False
            best = False

            destroy_prob = [x/sum(destroy_weights) for x in destroy_weights]
            repair_prob = [x/sum(repair_weights) for x in repair_weights]
            d_idx = random.choices(range(len(destroy_methods)),weights=destroy_prob)[0]
            print(f'Entering {destroy_methods[d_idx]}')
            destroy_method = destroy_methods[d_idx]
            r_idx = random.choices(range(len(repair_methods)),weights=repair_prob)[0]
            repair_method = repair_methods[r_idx]
            temp_sol = self.adaptive_destroy(cur_sol,method=destroy_method,cost_dict=cur_sol_costs, size=size, p=p)
            print(f'Entering {repair_methods[r_idx]}')
            temp_sol = self.adaptive_repair(temp_sol,method=repair_method, cost_dict=cur_sol_costs)
            temp_sol_obj, temp_sol_costs, temp_cost_spread = self.get_objective(temp_sol)

            # Collect data at each iteration
            timestamps.append(int(timer() - start_time))
            iterations.append(it)
            temp_sol_objs.append(temp_sol_obj)
            cur_sol_objs.append(cur_sol_obj)
            best_sol_objs.append(best_sol_obj)
            d_ws.append(destroy_weights)

            print(f'{it} - {temp_sol_obj} - {cur_sol_obj} - {best_sol_obj}')
            if temp_sol_obj < cur_sol_obj:
                better = True
            if self.adaptive_accept(temp_sol_obj, cur_sol_obj):
                accept = True
                cur_sol = temp_sol
                cur_sol_obj = temp_sol_obj
                cur_sol_costs = temp_sol_costs
                cur_cost_spread = temp_cost_spread
            if temp_sol_obj < best_sol_obj:
                best = True
                best_sol = temp_sol
                best_sol_obj = temp_sol_obj
                best_sol_costs = temp_sol_costs
                best_cost_spread = temp_cost_spread
            
            if best:
                destroy_weights[d_idx] = decay*destroy_weights[d_idx]+(1-decay)*w1
                repair_weights[r_idx] = decay*repair_weights[r_idx]+(1-decay)*w1
            elif better:
                destroy_weights[d_idx] = decay*destroy_weights[d_idx]+(1-decay)*w2
                repair_weights[r_idx] = decay*repair_weights[r_idx]+(1-decay)*w2
            elif accept:
                destroy_weights[d_idx] = decay*destroy_weights[d_idx]+(1-decay)*w3
                repair_weights[r_idx] = decay*repair_weights[r_idx]+(1-decay)*w3
            else:
                destroy_weights[d_idx] = decay*destroy_weights[d_idx]+(1-decay)*w4
                repair_weights[r_idx] = decay*repair_weights[r_idx]+(1-decay)*w4

            print(f'destroy_weights: {destroy_weights}')
            print(f'repair_weights: {repair_weights}')
            if it == 500 or timer()-start_time > 1000:
                repeat = False
        print('Best obj: ', best_sol_obj)
        return best_sol_obj,best_sol_objs,cur_sol_objs,temp_sol_objs,timestamps,iterations

    def adaptive_destroy(self, solution=None, size=0.20, p=0.8, cost_dict=None, method='random'):
        #get a random subset of the solution
        if solution == None:
            solution = self.solution
        subset = {}
        if method == 'random':
            subset = self.destroy(solution,size)
        elif method == 'room':
            removed = []
            n_size = int((size)*self.class_count_nc) #non_committed classes
            room_neigh, _ = self.get_neighborhood(solution)
            shuffled_rooms = list(room_neigh.keys())
            random.shuffle(shuffled_rooms)
            for room in shuffled_rooms:
                if len(room_neigh[room]) > 1:
                    random.shuffle(room_neigh[room])
                    while len(removed) < n_size and len(room_neigh[room]) > 0:
                        class_ = room_neigh[room].pop()
                        val = solution[class_]
                        if (class_,val[0],val[1]) in self.fixed_vars:
                            continue
                        subset[class_] = solution[class_]
                        removed.append(class_)
        elif method == 'worst':
            subset = solution.copy()
            removed = []
            n_size = int((size)*self.class_count_nc) #non_committed classes
            while len(removed) < n_size:
                _, subset_costs_dict, _ = self.get_objective(subset)
                sorted_costs = self.sort_dict_by_value(subset_costs_dict)
                for class_ in sorted_costs:
                    val = solution[class_]
                    if (class_,val[0],val[1]) in self.fixed_vars:
                        continue
                    if random.random() < p:
                        removed.append(subset.pop(class_))
                        break
        return subset

    def adaptive_repair(self, solution=None, cost_dict=None, method='standard'):
        if method == 'standard':
            return self.repair(solution)

    def adaptive_accept(self, temp_obj, cur_obj):
        if temp_obj < cur_obj:
            return True

    def get_neighborhood(self, solution):
        # make dict with classes in the same rooms
        room_neigborhood = {}
        for class_, (time, room) in solution.items():
            if self.classes[class_]['committed'] == 'true':
                continue
            if room not in room_neigborhood.keys():
                room_neigborhood[room] = []
            room_neigborhood[room].append(class_)

        # make list with classes pairs in overlapping time slots
        time_neigborhood = []
        class_pairs = list(itertools.combinations(solution.keys(), 2))
        for class_, class_bar in class_pairs:
            if self.classes[class_]['committed'] == 'true' or self.classes[class_bar]['committed'] == 'true':
                continue
            if self.time_overlap(solution[class_][0], solution[class_bar][0]):
                time_neigborhood.append((class_, class_bar))
        return room_neigborhood, time_neigborhood

    def save_list_as_txt(self,lists,instance, filename):
        with open(filename, 'w') as file:
            file.write('name: ' + instance + '\n')
            file.write('Iteration, Time, Temp, Current, Best\n')
            for items in zip(*lists):
                line = ', '.join(map(str, items)) + '\n'
                file.write(line)

    def generate_plots(self,lns,alns,instance, obj='best'):

     
        # Read data from lns
        data1 = np.genfromtxt(lns, delimiter=',', skip_header=1)

        # Read data from alns
        data2 = np.genfromtxt(alns, delimiter=',', skip_header=1)

        # Extract columns for plotting
        if obj == 'best':
            col = 4
        elif obj == 'temp':
            col = 2
        iteration1 = data1[:, 0]
        best1 = data1[:, col] 

        iteration2 = data2[:, 0]
        best2 = data2[:, col] 

        # Create a plot comparing the 'Best' values from both files
        plt.plot(iteration1, best1, label='LNS')
        plt.plot(iteration2, best2, label='ALNS')
        plt.xlabel('Iteration')
        plt.ylabel('Repaired')
        plt.legend()
        caption = instance
        plt.figtext(0.5, 0.95, caption, wrap=True, horizontalalignment='center', fontsize=12)
        # Save the plot as a file in the specified folder
        plt.savefig(os.path.join('Data/graph_results', f"{obj}_{instance}.png"))
        plt.show()


        
if __name__ == "__main__":

    model = TimetablingProblem()

    data_folder = "Data/data instances"
    files = os.listdir('Data/data instances')


    files.sort()
    infeasible = []
    for file in files:
        # Load and process the file
        file_path = os.path.join(data_folder, file)
        if file_path.endswith('.xml'):
            data = model.read_data(file_path, data_type='unitime') #read the data
            model.create_unitime_model() #create the model
            model.solve() #solve the model
            init_sol = model.save_solution() #save the solution
            best_sol_obj,best_sol_objs,cur_sol_objs,temp_sol_objs,timestamps,iterations = model.large_neighborhood_search(init_sol.copy()) #run the lns
            model.save_list_as_txt([iterations,timestamps,temp_sol_objs,cur_sol_objs,best_sol_objs],file,f'Data/Results/lns_{file}.txt') #save the results
            best_sol_obj,best_sol_objs,cur_sol_objs,temp_sol_objs,timestamps,iterations = model.adaptive_neighborhood_search(init_sol.copy())  #run the alns
            model.save_list_as_txt([iterations,timestamps,temp_sol_objs,cur_sol_objs,best_sol_objs],file,f'Data/Results/alns_{file}.txt') #save the results


            file = file[:-4]
            model.generate_plots(f'Data/Results/lns_{file}test.xml.txt',f'Data/Results/alns_{file}.xml.txt',file,obj='best') #generate the 'best' plots
            model.generate_plots(f'Data/Results/lns_{file}test.xml.txt',f'Data/Results/alns_{file}.xml.txt',file,obj='temp') #generate the 'temp' plots



    # list_of_paths = [os.path.join(data_folder, file) for file in files if file.endswith('.xml')]
    # print(model.create_department_table(list_of_paths)) #create the department table

