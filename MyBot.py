#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

from itertools import chain
""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

all_positions = [hlt.Position(y=y, x=x) for x in range(game.game_map.width) for y in range(game.game_map.height)]

ship_status = {}
ship_target = {}
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("MyPythonBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))


class Status:
    Exploring = 'exploring'
    Collecting = 'collecting'
    Returning = 'returning'  # with potentially different drop-offs
    Building = 'building'  # build a new drop-off
    Hunting = 'hunting'
    Fighting = 'fighting'


# send ship to ennemy base if 2 players
hunter = True
if len(game.players.keys()) == 2:
    hunter = False  # False so I need a hunter
    hunter = True


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


while game.turn_number < (constants.MAX_TURNS - game.game_map.height / 2):
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
