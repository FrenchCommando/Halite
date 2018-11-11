#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position

# This library allows you to generate random numbers.
import random
# import time
from itertools import product

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

from itertools import chain
""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()


# shield_size = 5  # range of protection of the base


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
game.ready("MyPythonBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))


while True:
    # start = time.time()
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

    # Assigning Still to each ship that has not enough fuel to move
    # To avoid having to perform a check every time you need to make a move
    for ship in ships.copy():
        if ship.halite_amount <= game_map[ship.position].halite_amount / 10 \
                and game_map[ship.position].halite_amount != 0:
            command_queue.append(ship.move(Direction.Still))
            next_occupied.add(normalize_position(ship.position))
            ships.remove(ship)


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
        ships.sort(key=lambda my_ship: my_ship.halite_amount, reverse=False)

        remaining_ships = [s for s in ships]
        # all we need is a mapping of ships to moves that make everyone happy
        # search in a tree that maximizes a utility function

        search_range = min(max(5, game.turn_number // 2), game_map.height // 2 + 1)

        # end = time.time()
        # logging.info("Pre - FindMax-Threshold\t" + str(round((end - start) * 1000)))

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
        max_halite = max(game_map[p].halite_amount for p in checked_positions())
        low_threshold = round(min(50, max_halite / 10)) + 1
        logging.info('{} - {}'.format(max_halite, low_threshold))

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
        adjacent_cells = set()
        # it's a table not a set
        cleared_path = [[False for y in range(height)] for x in range(width)]
        # contains tuples of (x,y)
        path_queue = set(normalize_position(entity.position) for entity in chain([me.shipyard], me.get_dropoffs()))

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

        def find_closest_home(position):
            homes = list(chain([me.shipyard], me.get_dropoffs()))
            homes.sort(key=lambda target: game_map.calculate_distance(position, target.position), reverse=True)
            return homes[0].position

        l_adjacent_cells = list(adjacent_cells)

        def decision(ship):
            # returns a list of priority moves with corresponding destination
            rep = []
            ship_position = ship.position
            ship_halite = ship.halite_amount

            to_assign = set(chain([Direction.Still], Direction.get_all_cardinals()))

            for u in to_assign.copy():
                if normalize_position(ship_position.directional_offset(u)) in basic_occupied_cells:
                    to_assign.remove(u)

            map_to_cell = {d: ship_position.directional_offset(d) for d in to_assign}

            def assign(move):
                if move in to_assign:
                    rep.append((move, normalize_position(map_to_cell[move])))
                    to_assign.remove(move)

            def assign_still():
                assign(Direction.Still)

            def go_home():
                home_position = find_closest_home(ship_position)
                moves = game_map.get_unsafe_moves(ship_position, home_position)
                for move in moves:
                    assign(move)

            cell_halite = game_map[ship_position].halite_amount

            if ship_halite == constants.MAX_HALITE:
                go_home()
                assign_still()  # learn to wait in line
                # return rep

            elif ship_halite >= constants.MAX_HALITE * 9 / 10:
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
                return 1 * game_map[my_position].halite_amount - 10 * distance

            if len(adjacent_cells) > 0:
                l_adjacent_cells.sort(key=my_utility, reverse=True)
                tx, ty = max(l_adjacent_cells, key=my_utility)
                moves = game_map.get_unsafe_moves(ship_position, Position(x=tx, y=ty))
                for move in moves:
                    assign(move)

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
        # logging.info("Pre - Mapping \t" + str(round((end - start) * 1000)))
        # end = time.time()
        # if (end - start) > 1.5:
        #     break

        ship_mapping = {ship.id: decision(ship) for ship in remaining_ships}

        def choose_moves(u):
            for ship, (move, cell) in zip(remaining_ships, u):
                command_queue.append(ship.move(move))


        # end = time.time()
        # logging.info(end-start)
        # if (end - start) > 1.9:
        #     game.end_turn(command_queue)
        #     break

        # end = time.time()
        # logging.info("Pre - tree\t" + str(round((end - start) * 1000)))
        solved = False
        # this is very bad - youre going through the whole tree - not even cutting the branches
        for u in product(*[ship_mapping[ship.id] for ship in remaining_ships]):
            # end = time.time()
            # if (end - start) > 1.5:
            #     game.end_turn(command_queue)
            #     break
            all_occupied = set()  # basic_occupied_cells.copy()

            wrong = False
            for (move, (cell_x, cell_y)) in u:
                if (cell_x, cell_y) in all_occupied:
                    wrong = True
                    break
                else:
                    all_occupied.add((cell_x, cell_y))
            if wrong:
                continue
            choose_moves(u)
            solved = True

            break

        # logging.info(count)
        # end = time.time()
        # logging.info(end-start)
        # if (end - start) > 1.9:
        #     game.end_turn(command_queue)

        # end = time.time()
        # logging.info("Post Tree\t" + str(round((end - start) * 1000)))
        # end = time.time()
        # if (end - start) > 1.5:
        #     game.end_turn(command_queue)
        #     break

        if not solved:
            for ship in remaining_ships:
                logging.info("Ship {} - position {} {}".format(ship.id, ship.position.x, ship.position.y))
            logging.info("Not Solvec")
            for x, y in adjacent_cells:
                logging.info('Adjacent {} - {}'.format(x, y))
            for ship in remaining_ships:
                command_queue.append(ship.move(Direction.Still))
                all_occupied.add(normalize_position(ship.position))
            # do something
            # pass

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if (constants.MAX_TURNS - game.turn_number >= 200 or game.turn_number <= 250) \
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

    if not game.turn_number < 100:  # (constants.MAX_TURNS - game.game_map.height / 2):
        break

    # Scan for ship that are already heavily loaded
    # if it is fully full, send it back (use a smart way to find the path)

    # if it is above a certain threshold load_threshold
    # - check if there is some minerals to loot on the current position / or the adjacent positions
    # - if there is enough to be lucrative (in the following sense) keep looting
    # - remaining quantity has to be below a threshold - collect_ignore
    # Status : Returning or Collecting
    # At his point, targets have been assigned to ships that are heavily loaded

    # What about regular ships "Exploring" or "Collecting-but-not-enough"
    # Exploring ships should be able to push collecting ships that are standing still
    # Keep pushing - pushing - pushing
    # Global assignment of targets
    # Only use paths on clear paths - minerals below target_ignore

# think about
# A fight leading to high amount of minerals at some point - have to jump on it
# - that's why target allocations is done at every turn
# One high mineral sorrounded by a lesser but still high mineral content
# - Don't jump on the big guy - process the surrounding first to clear a path


# ############# below is older code ##############
#
# # send ship to ennemy base if 2 players - That's bullshit - Find something smarter
hunter = True
# if len(game.players.keys()) == 2:
#     hunter = False  # False so I need a hunter
#     hunter = True
# # end : stupid hunting strategy
#

all_positions = [Position(y=y, x=x) for x in range(game.game_map.width) for y in range(game.game_map.height)]


ship_status = {}
ship_target = {}


class Status:
    Exploring = 'exploring'
    Collecting = 'collecting'
    Returning = 'returning'  # with potentially different drop-offs
    Building = 'building'  # build a new drop-off
    Hunting = 'hunting'
    Fighting = 'fighting'


def less_naive_navigate(ship, destination):
    """
    Returns a singular safe move towards the destination. -> forces to move if blocked

    :param ship: The ship to move.
    :param destination: Ending position
    :return: A direction.
    """

    if ship.halite_amount <= game_map[ship.position].halite_amount / 10 \
            and game_map[ship.position].halite_amount != 0:
        return Direction.Still
    # No need to normalize destination, since get_unsafe_moves
    # does that
    moves = game_map.get_unsafe_moves(ship.position, destination)
    if len(moves) == 0:
        return Direction.Still

    for direction in chain(moves,
                           iter([random.choice(
                               [Direction.North, Direction.South, Direction.East, Direction.West])])):
        target_pos = ship.position.directional_offset(direction)
        if not game_map[target_pos].is_occupied:
            game_map[ship.position].ship = None
            game_map[target_pos].mark_unsafe(ship)
            return direction
    return Direction.Still


def even_less_naive_navigate(ship, destination):
    """
    Returns a singular safe move towards the destination.

    :param ship: The ship to move.
    :param destination: Ending position
    :return: A direction.
    """
    if ship.halite_amount <= game_map[ship.position].halite_amount / 10 \
            and game_map[ship.position].halite_amount != 0:
        # deadlock if a ship lands on a position with too many minerals
        return Direction.Still
    # No need to normalize destination, since get_unsafe_moves
    # does that
    for direction in game_map.get_unsafe_moves(ship.position, destination):
        target_pos = ship.position.directional_offset(direction)
        if not game_map[target_pos].is_occupied:
            game_map[ship.position].ship = None
            game_map[target_pos].mark_unsafe(ship)
            return direction

    return Direction.Still


""" <<<Game Loop>>> """


# while game.turn_number < (constants.MAX_TURNS - game.game_map.height / 2):
while game.turn_number < (constants.MAX_TURNS - max(len(me.get_ships()), game_map.height) // 2):
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # quantiles
    max_value = max([game_map[position].halite_amount for position in all_positions])
    quantile = min(0.01 * max_value, 50)
    ignored_quantity = quantile  # * (constants.MAX_TURNS - game.turn_number) / constants.MAX_TURNS

    def get_target_position(current_position):
        def amount_order(position):
            if game_map[position].has_structure:
                return -1000000000
            amount = game_map[position].halite_amount
            distance = game_map.calculate_distance(position, current_position)
            distance_shipyard = game_map.calculate_distance(position, me.shipyard.position)
            if game.turn_number <= 0:
                if amount <= 0:
                    return -10000000
            else:
                if amount <= ignored_quantity:
                    return -10000000

            return amount - quantile * (distance + distance_shipyard * 3) * 100 / game_map.height
        all_positions.sort(key=lambda x: amount_order(x), reverse=True)
        return iter(all_positions)

    def get_next_target(current_position):
        iter_position = get_target_position(current_position)
        new_position = next(iter_position)
        while new_position in ship_target.values():
            new_position = next(iter_position)
        return new_position

    ennemy_target = []
    for player in game.players.values():
        if player is not me:
            ennemy_target.append(player.shipyard.position)
            for dropoff in player.get_dropoffs():
                ennemy_target.append(dropoff.position)
    iter_ennemy = iter(ennemy_target)

    # # careful destroyed ships
    # available_ships = [ship.id for ship in me.get_ships()]
    # for _id in ship_status:
    #     if _id not in available_ships:
    #         ship_status.pop(_id)
    #         ship_target.pop(_id)

    # destroy ennemy ship in base

    # build new drop-off

    for ship in me.get_ships():

        if ship.id not in ship_status:
            if not hunter:
                hunter = True
                ship_status[ship.id] = Status.Hunting
                ship_target[ship.id] = next(iter_ennemy)
            else:
                ship_status[ship.id] = Status.Exploring
                ship_target[ship.id] = get_next_target(ship.position)
        elif ship_status[ship.id] == Status.Hunting:
            pass
        elif ship_status[ship.id] == Status.Returning:
            if ship.position == me.shipyard.position:
                ship_status[ship.id] = Status.Exploring
                ship_target[ship.id] = get_next_target(ship.position)
        elif ship_status[ship.id] == Status.Exploring:
            if ship.position == ship_target[ship.id]:
                ship_status[ship.id] = Status.Collecting
        elif ship_status[ship.id] == Status.Collecting:
            if ship.halite_amount >= constants.MAX_HALITE * 0.75:
                ship_status[ship.id] = Status.Returning
                ship_target[ship.id] = me.shipyard.position
            elif game_map[ship.position].halite_amount <= ignored_quantity / 2:
                ship_status[ship.id] = Status.Exploring
                ship_target[ship.id] = get_next_target(ship.position)

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []
    solved = set()

    for ship in me.get_ships():
        if ship.position == me.shipyard.position:
            directions = game_map.get_unsafe_moves(ship.position, ship_target[ship.id])
            for u in directions:
                if not game_map[ship.position.directional_offset(u)].is_occupied:
                    game_map[ship.position].ship = None
                    game_map[ship.position.directional_offset(u)].mark_unsafe(ship)
                    command_queue.append(ship.move(u))
                    solved.add(ship.id)
                    break
                else:
                    second_ship = game_map[ship.position.directional_offset(u)].ship
                    if second_ship.id not in ship_status:  # maybe ennemy
                        game_map[second_ship.position].ship = ship
                        command_queue.append(ship.move(u))
                        solved.add(ship.id)
                        # solved.add(second_ship.id)
                        break
                    elif ship_status[second_ship.id] == Status.Returning:
                        game_map[ship.position].ship = second_ship
                        game_map[second_ship.position].ship = ship
                        command_queue.append(ship.move(u))
                        command_queue.append(second_ship.move(Direction.invert(u)))
                        solved.add(ship.id)
                        solved.add(second_ship.id)
                        break
            break

    for ship in me.get_ships():
        if ship.id not in solved and ship_status[ship.id] == Status.Hunting:
            move = even_less_naive_navigate(ship, ship_target[ship.id])
            command_queue.append(ship.move(move))
            solved.add(ship.id)

    for ship in me.get_ships():
        if ship.id not in solved and ship_status[ship.id] == Status.Returning:
            move = even_less_naive_navigate(ship, ship_target[ship.id])
            command_queue.append(ship.move(move))
            solved.add(ship.id)

    for ship in me.get_ships():
        if ship.id not in solved and ship_status[ship.id] == Status.Collecting:
            command_queue.append(ship.move(Direction.Still))
            solved.add(ship.id)

    for ship in me.get_ships():
        if ship.id not in solved and ship_status[ship.id] == Status.Exploring:
            move = less_naive_navigate(ship, ship_target[ship.id])
            command_queue.append(ship.move(move))
            solved.add(ship.id)

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if (constants.MAX_TURNS - game.turn_number >= 200 or game.turn_number <= 200) \
            and me.halite_amount >= constants.SHIP_COST \
            and not game_map[me.shipyard].is_occupied\
            and len(me.get_ships()) <= game_map.height:
        command_queue.append(me.shipyard.spawn())

    for ship in me.get_ships():
        logging.info(ship_status[ship.id])

    for ship in me.get_ships():
        logging.info('-'.join(map(lambda x: str(x), [ship.id, ship.position.x, ship.position.y])))

    for u in command_queue:
        logging.info(u)

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)


while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []

    # crash all the ships into base if close to the end
    destination = me.shipyard.position
    # logging.info(str(constants.MAX_TURNS))
    # occupied_cells = set()  # one cell can have several coordinates
    for ship in me.get_ships():
        move_list = game_map.get_unsafe_moves(ship.position, destination)
        if len(move_list) > 0:
            target_cell = ship.position.directional_offset(move_list[0])
            if target_cell == destination:
                command_queue.append(ship.move(move_list[0]))
            else:
                move = even_less_naive_navigate(ship, destination)
                command_queue.append(ship.move(move))
            # elif (target_cell.x, target_cell.y) not in occupied_cells:
            #     occupied_cells.add((target_cell.x, target_cell.y))
            #     command_queue.append(ship.move(move_list[0]))
            # continue
        else:
            command_queue.append(ship.move(Direction.Still))
    game.end_turn(command_queue)
