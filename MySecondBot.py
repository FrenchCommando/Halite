#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position

# This library allows you to generate random numbers.
import time

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

from itertools import chain
""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()


def normalize_position(position):
    return position.x % game_map.width, position.y % game_map.height


# should depend on threshold criterion
me = game.me
game_map = game.game_map

height = game_map.height
width = game_map.width


# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.

# build a score map - containing the sum of halites on a specified range for each cell
score_range = int(game_map.height / 5)


def get_score(x, y):
    def my_iter():
        for xx in range(-score_range, score_range):
            for yy in range(-score_range, score_range):
                yield Position(x=x+xx, y=y+yy)
    return sum(game_map[pos].halite_amount for pos in my_iter())


score_map = [[get_score(x, y) for y in range(height)] for x in range(width)]
max_score = max(max(score_map))
score_map = [[u / max_score for u in v] for v in score_map]

game.ready("MySecondBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))


def find_closest_home(position):
    homes = list(chain([me.shipyard], me.get_dropoffs()))
    homes.sort(key=lambda target: game_map.calculate_distance(position, target.position), reverse=False)
    return homes[0].position


def priority_move(ship, target):
    """
      Returns a singular safe move towards the destination.
      False if it can't move (not enough halite)

      :param ship: The ship to move.
      :param destination: Ending position
      :return: True - or False
      """
    # No need to normalize destination, since get_unsafe_moves
    # does that
    moves = game_map.get_unsafe_moves(ship.position, target)
    for move in moves:
        destination = normalize_position(ship.position.directional_offset(move))
        if destination not in next_occupied:
            command_queue.append(ship.move(move))
            next_occupied.add(destination)
            ships.remove(ship)
            return True
    return False


built_dropoff = False


while True:
    start = time.time()
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.

    # contains the remaining ships to assign
    ships = [ship for ship in me.get_ships()]

    # cells occupied at next turn - to avoid collisions
    next_occupied = set()

    # This is the command queue
    command_queue = []

    search_range = min(max(5, game.turn_number // 2), game_map.height // 2 + 1)

    def checked_positions():
        """Generator for positions to check for ennemies"""
        for base_position in chain([me.shipyard], me.get_dropoffs()):
            x_shipyard = base_position.position.x
            y_shipyard = base_position.position.y
            for x in range(-search_range, search_range):
                for y in range(-search_range, search_range):
                    yield hlt.Position(
                        x=x_shipyard + x,
                        y=y_shipyard + y)


    max_halite, pos = max([(game_map[p].halite_amount, p) for p in checked_positions()], key=lambda x: x[0])
    low_threshold = round(min(50, max_halite / 10)) + 1
    # logging.info('{} - {}'.format(max_halite, low_threshold))

    if not built_dropoff:
        if game.turn_number >= 200 and max_halite >= 500 and (constants.MAX_TURNS - game.turn_number) >= 50:
            # convert the ship with highest distance to base
            if len(ships) > 0:
                ships.sort(key=lambda ship: height * score_map[ship.position.x][ship.position.y]
                           + game_map.calculate_distance(ship.position, me.shipyard.position))
                selected_ship = ships[-1]
                if me.halite_amount + game_map[selected_ship.position].halite_amount + selected_ship.halite_amount \
                        >= 4000 + 1000:
                    command_queue.append(selected_ship.make_dropoff())
                    ships.remove(selected_ship)
                    built_dropoff = True
                    # careful not to build a ship at that round
                    # thus the 1000 buffer

    # Assigning Still to each ship that has not enough fuel to move
    # To avoid having to perform a check every time you need to make a move
    for ship in ships.copy():
        if ship.halite_amount <= game_map[ship.position].halite_amount / 10 \
                and game_map[ship.position].halite_amount != 0:
            command_queue.append(ship.move(Direction.Still))
            next_occupied.add(normalize_position(ship.position))
            ships.remove(ship)

    # end = time.time()
    # logging.info("Post Find Immobile\t" + str(round((end - start) * 1000)))

    # # Scan for ennemies within shield_size of the shipyard
    # # Send ships to attack and destroy them (like a kamikaze)
    # # Status : Fighting
    # def shield_base():
    #     for base_position in chain([me.shipyard], me.get_dropoffs()):
    #         x_shipyard = base_position.position.x
    #         y_shipyard = base_position.position.y
    #
    #         def checked_positions():
    #             """Generator for positions to check for ennemies"""
    #             for x in range(-shield_size, shield_size):
    #                 for y in range(-shield_size, shield_size):
    #                     yield Position(
    #                         x=(x_shipyard + x) % game_map.width,
    #                         y=(y_shipyard + y) % game_map.height)
    #
    #         occupied_position = [position for position in checked_positions()
    #                              if game_map[position].ship is not None
    #                              and game_map[position].ship.owner != me.id]
    #
    #         # find the closest ally ship from a target
    #         for target_position in occupied_position:
    #             ships.sort(key=lambda my_ship: game_map.calculate_distance(my_ship.position, target_position))
    #             for ship in ships.copy():
    #                 if priority_move(ship, target_position):
    #                     break
    #             # what if not targeted ?
    #     return
    # shield_base()

    # that's useless
    basic_occupied_cells = set(next_occupied)

    # for x, y in basic_occupied_cells:
    #     logging.info('Occupied {} - {}'.format(x, y))

    all_occupied = set()  # basic_occupied_cells.copy()

    if len(ships) != 0:
        # not sure how to prioritize them
        def distance_to_base(position):
            base = find_closest_home(position)
            return game_map.calculate_distance(position, base)
        ships.sort(key=lambda my_ship: distance_to_base(my_ship.position), reverse=False)

        remaining_ships = [s for s in ships]
        # all we need is a mapping of ships to moves that make everyone happy
        # search in a tree that maximizes a utility function

        # end = time.time()
        # logging.info("PostFindMax\t" + str(round((end - start) * 1000)))
        # logging.info("range{} max{} threshold{}\t".format(str(search_range), str(max_halite), str(low_threshold)))

        # if game.turn_number != 1:
        #     for c in adjacent_cells.copy():
        #         x, y = c
        #         p = Position(x=x, y=y)
        #         if game_map[p].halite_amount <= low_threshold:
        #             adjacent_cells.remove(c)
        #             path_queue.add(c)
        # # all cells that are accessible from the shipyard or dropoffs

        # end = time.time()
        # logging.info("Pre - AdjacentCells\t" + str(round((end - start) * 1000)))
        # cleared_path contains the cells with halite amount below the threshold
        # contains tuples of (x,y)

        # ################################################## part about adjacent_cells
        adjacent_cells = set()
        # it's a table not a set
        cleared_path = [[False for y in range(height)] for x in range(width)]
        # contains tuples of (x,y)
        path_queue = set(normalize_position(entity.position) for entity in chain([me.shipyard], me.get_dropoffs()))

        # end = time.time()
        # logging.info("PreFindAdjacent\t" + str(round((end - start) * 1000)))

        while len(path_queue) != 0:
            x, y = path_queue.pop()
            cleared_path[x][y] = True
            p = Position(x=x, y=y)
            # if game_map.calculate_distance(p, me.shipyard.position) < 10:  # why not
            for u in p.get_surrounding_cardinals():
                u_x, u_y = normalize_position(u)
                if game_map[u].halite_amount <= low_threshold:
                    if not cleared_path[u_x][u_y]:
                        path_queue.add((u_x, u_y))
                else:
                    adjacent_cells.add((u_x, u_y))

        # end = time.time()
        # logging.info("PostFindMax\t" + str(round((end - start) * 1000)))

        l_adjacent_cells = list(adjacent_cells)
        #####################################################

        # exploring ships will target adjacent cells and avoid cleared_path
        # returning ships must stay in cleared_path
        # collecting ships will stay in adjacent cells and avoid cleared_path
        # for x, y in adjacent_cells:
        #     logging.info('Adjacent {} - {}'.format(x, y))
        # for x,y in cleared_path:
        #     logging.info('Cleared {} - {}'.format(x, y))

        # end = time.time()
        # if (end - start) > 1.5:
        #     game.end_turn(command_queue)
        #     break
        # logging.info("Post - AdjacentCells\t" + str(round((end - start) * 1000)))

        def decision(ship):
            # returns a list of priority moves with corresponding destination
            rep = []
            ship_position = ship.position
            ship_halite = ship.halite_amount

            to_assign = set(chain([Direction.Still], Direction.get_all_cardinals()))

            for one_move in to_assign.copy():
                if normalize_position(ship_position.directional_offset(one_move)) in basic_occupied_cells:
                    to_assign.remove(one_move)

            # logging.info("Position - {}{}".format(ship_position.x, ship_position.y))
            # for u, v in to_assign:
            #     logging.info("{}{}".format(str(u), str(v)))

            map_to_cell = {d: ship_position.directional_offset(d) for d in to_assign}

            def assign(move):
                if move in to_assign:
                    rep.append((move, normalize_position(map_to_cell[move])))
                    to_assign.remove(move)

            def assign_still():
                assign(Direction.Still)

            def go_home():
                home_position = find_closest_home(ship_position)
                moves = game_map.get_unsafe_moves(ship_position, home_position)[::-1]  # invert x/y priority on return
                for move in moves:
                    assign(move)
                if len(moves) == 1:
                    assign_still()
                    my_move = moves[0]
                    to_assign.discard(Direction.invert(my_move))  # don't walk back, but you can go on the sides

            cell_halite = game_map[ship_position].halite_amount

            if ship_halite == constants.MAX_HALITE:
                go_home()
                assign_still()  # learn to wait in line
                # return rep

            elif ship_halite >= constants.MAX_HALITE * 4 // 5:  # can't be more than 90%, or it's gonna loop
                # need some double threshold for hysteresis
                # but this is rare, if you lose some halite, you're gonna pick up more at the next round
                if cell_halite >= low_threshold:
                    assign_still()
                    go_home()
                    # return rep
                else:
                    go_home()
                    if cell_halite != 0:
                        assign_still()
                    # return rep

            if cell_halite >= low_threshold:
                assign_still()

            def my_utility(target_position):
                x, y = target_position
                my_position = Position(x=x, y=y)
                distance = game_map.calculate_distance(ship_position, my_position)
                return 1 * game_map[my_position].halite_amount - 100 * distance + score_map[x][y] * max_halite

            if len(adjacent_cells) > 0:
                # l_adjacent_cells.sort(key=my_utility, reverse=True)
                # tx, ty = l_adjacent_cells[0]
                tx, ty = max(l_adjacent_cells, key=my_utility)
                moves = game_map.get_unsafe_moves(ship_position, Position(x=tx, y=ty))
                for move in moves:
                    assign(move)
            # moves = game_map.get_unsafe_moves(ship_position, Position(x=pos.x, y=pos.y))
            # for move in moves:
            #     assign(move)

            for move in to_assign.copy():
                if game_map[map_to_cell[move]].halite_amount >= low_threshold:
                    assign(move)

            if len(rep) == 0:
                l_to_assign = list(to_assign)

                def halite_in_target(move):
                    u = map_to_cell[move]
                    return game_map[u].halite_amount
                l_to_assign.sort(key=halite_in_target, reverse=True)

                for move in l_to_assign:
                    assign(move)

            assign_still()  # learn to wait in line

            # for move, (x, y) in rep:
            #     logging.info('Rep {} {} - {} - {}'.format(ship.id, move, x, y))

            return rep


        # end = time.time()
        # logging.info("PostDecisionDefinition\t" + str(round((end - start) * 1000)))

        # end = time.time()
        # logging.info("Pre - Mapping \t" + str(round((end - start) * 1000)))
        # end = time.time()
        # if (end - start) > 1.5:
        #     break

        ship_mapping = {ship.id: decision(ship) for ship in remaining_ships}

        # end = time.time()
        # logging.info("PostDecisionRun\t" + str(round((end - start) * 1000)))

        # def choose_moves(u):
        #     for ship, (move, cell) in zip(remaining_ships, u):
        #         command_queue.append(ship.move(move))

        # end = time.time()
        # logging.info(end-start)
        # if (end - start) > 1.9:
        #     game.end_turn(command_queue)
        #     break

        # end = time.time()
        # logging.info("Pre - tree\t" + str(round((end - start) * 1000)))
        solved = False
        # this is very bad - youre going through the whole tree - not even cutting the branches

        ship_number = len(remaining_ships)

        l_moves = [ship_mapping[remaining_ships[i].id][0][0] for i in range(ship_number)]
        l_occupied = [ship_mapping[remaining_ships[i].id][0][1] for i in range(ship_number)]

        # def get_optimal_leaf(n):
        # This idea is bad, too many casualties
        def get_optimal_leaf(n, counter=[100]):
            counter[0] -= 1
            if counter[0] == 0:
                # global l_moves, l_occupied
                # l_moves = [ship_mapping[remaining_ships[i].id][0][0] for i in range(ship_number)]
                # l_occupied = [ship_mapping[remaining_ships[i].id][0][1] for i in range(ship_number)]
                return False
            if n == ship_number:
                return True
            mapping_value = ship_mapping[remaining_ships[n].id]
            for my_move, my_cell in mapping_value:
                if my_cell not in l_occupied[:n]:
                    l_moves[n] = my_move
                    l_occupied[n] = my_cell
                    rep = get_optimal_leaf(n + 1)
                    if rep:
                        return rep
            return False

        # end = time.time()
        # logging.info("PreInitLeaf\t" + str(round((end - start) * 1000)))

        def choose_moves_simple(u):
            for ship, move in zip(remaining_ships, u):
                command_queue.append(ship.move(move))

        # do something by clusters of adjacent ships
        if get_optimal_leaf(0):
            solved = True
            all_occupied = set(l_occupied)
            choose_moves_simple(l_moves)

        # end = time.time()
        # logging.info("PostLeafChooseMoves\t" + str(round((end - start) * 1000)))

        if not solved:
            # for ship in remaining_ships:
            #     logging.info("Ship {} - position {} {}".format(ship.id, ship.position.x, ship.position.y))
            # logging.info("Not Solvec")
            # for x, y in adjacent_cells:
            #     logging.info('Adjacent {} - {}'.format(x, y))
            for ship in remaining_ships:
                command_queue.append(ship.move(Direction.Still))
                all_occupied.add(normalize_position(ship.position))
            # do something
            # pass

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if (constants.MAX_TURNS - game.turn_number >= 200 or game.turn_number <= 300) \
            and me.halite_amount >= constants.SHIP_COST \
            and not normalize_position(me.shipyard.position) in all_occupied \
            and not normalize_position(me.shipyard.position) in basic_occupied_cells \
            and len(me.get_ships()) <= game_map.height:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

    # end = time.time()
    # logging.info("\t" + str(round((end - start) * 1000)))

    # for u in command_queue:
    #     logging.info(u)

    # if not game.turn_number < 100:  # (constants.MAX_TURNS - game.game_map.height / 2):
    if not game.turn_number < (constants.MAX_TURNS - game.game_map.height / 2):
        break


while True:
    game.update_frame()
    ships = [ship for ship in me.get_ships()]

    # cells occupied at next turn - to avoid collisions
    next_occupied = set()

    # This is the command queue
    command_queue = []

    # Assigning Still to each ship that has not enough fuel to move
    # To avoid having to perform a check every time you need to make a move
    for ship in ships.copy():
        if ship.halite_amount <= game_map[ship.position].halite_amount / 10 \
                and game_map[ship.position].halite_amount != 0:
            command_queue.append(ship.move(Direction.Still))
            next_occupied.add(normalize_position(ship.position))
            ships.remove(ship)

    for ship in ships.copy():
        ship_position = ship.position
        base = find_closest_home(ship_position)
        if (ship_position.x - base.x) % width == 0:
            if (ship_position.y - base.y) % height == 0:  # stay at the base
                ships.remove(ship)
                continue
            dy = (ship_position.y - base.y) % height
            if dy == 1:
                command_queue.append(ship.move(Direction.North))
                ships.remove(ship)
                continue
            if dy == height - 1:
                command_queue.append(ship.move(Direction.South))
                ships.remove(ship)
                continue
        if (ship_position.y - base.y) % height == 0:
            dx = (ship_position.x - base.x) % width
            if dx == 1:
                command_queue.append(ship.move(Direction.West))
                ships.remove(ship)
                continue
            if dx == width - 1:
                command_queue.append(ship.move(Direction.East))
                ships.remove(ship)
                continue

    # that's useless
    basic_occupied_cells = set(next_occupied)

    all_occupied = set()  # basic_occupied_cells.copy()

    if len(ships) != 0:
        # not sure how to prioritize them
        ships.sort(key=lambda my_ship: my_ship.halite_amount, reverse=False)

        remaining_ships = [s for s in ships]
        # all we need is a mapping of ships to moves that make everyone happy
        # search in a tree that maximizes a utility function

        def decision(ship):
            # returns a list of priority moves with corresponding destination
            rep = []
            ship_position = ship.position
            ship_halite = ship.halite_amount

            to_assign = set(chain([Direction.Still], Direction.get_all_cardinals()))

            for one_move in to_assign.copy():
                if normalize_position(ship_position.directional_offset(one_move)) in basic_occupied_cells:
                    to_assign.remove(one_move)

            map_to_cell = {d: ship_position.directional_offset(d) for d in to_assign}

            def assign(move):
                if move in to_assign:
                    rep.append((move, normalize_position(map_to_cell[move])))
                    to_assign.remove(move)

            def assign_still():
                assign(Direction.Still)

            def go_home():
                home_position = find_closest_home(ship_position)
                moves = game_map.get_unsafe_moves(ship_position, home_position)[::-1]  # invert x/y priority on return
                for move in moves:
                    assign(move)
                if len(moves) == 1:
                    assign_still()
                    my_move = moves[0]
                    to_assign.discard(Direction.invert(my_move))  # don't walk back, but you can go on the sides

            if ship_halite >= 0:
                go_home()
                assign_still()  # learn to wait in line
                # return rep
            else:
                for move in to_assign:
                    assign(move)

            return rep

        ship_mapping = {ship.id: decision(ship) for ship in remaining_ships}

        solved = False

        ship_number = len(remaining_ships)

        l_moves = [ship_mapping[remaining_ships[i].id][0][0] for i in range(ship_number)]
        l_occupied = [ship_mapping[remaining_ships[i].id][0][1] for i in range(ship_number)]

        s_base = set(chain([me.shipyard], me.get_dropoffs()))

        def get_optimal_leaf(n, counter=[100]):
            counter[0] -= 1
            if counter[0] == 0:
                return False
            if n == ship_number:
                return True
            mapping_value = ship_mapping[remaining_ships[n].id]
            for my_move, my_cell in mapping_value:
                if my_cell not in l_occupied[:n] or my_cell in s_base:
                    l_moves[n] = my_move
                    l_occupied[n] = my_cell
                    rep = get_optimal_leaf(n + 1)
                    if rep:
                        return rep
            return False

        def choose_moves_simple(u):
            for ship, move in zip(remaining_ships, u):
                command_queue.append(ship.move(move))

        # do something by clusters of adjacent ships
        if get_optimal_leaf(0):
            solved = True
            choose_moves_simple(l_moves)

        if not solved:
            # for ship in remaining_ships:
            #     logging.info("Ship {} - position {} {}".format(ship.id, ship.position.x, ship.position.y))
            # logging.info("Not Solvec")
            # for x, y in adjacent_cells:
            #     logging.info('Adjacent {} - {}'.format(x, y))
            for ship in remaining_ships:
                command_queue.append(ship.move(Direction.Still))
                all_occupied.add(normalize_position(ship.position))
            # do something
            # pass

    # crash all the ships into base if close to the end
    game.end_turn(command_queue)
