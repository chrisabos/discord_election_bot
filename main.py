import discord
from discord.ext import tasks, commands

import json
import schedule
import asyncio
from datetime import datetime

import config_handler as config
import data_handler as data

intents = discord.Intents.default()
intents.members = True
d_bot = commands.Bot(command_prefix='!', intents=intents)

async def is_president(ctx):
    return d_bot.guilds[0].get_role(config.get('role_id_el_presidente')) in ctx.author.roles

@d_bot.event
async def on_ready():
    print(f'Bot has connected to Discord as {d_bot.user}')

@d_bot.event
async def on_message(msg):
    if msg.author == d_bot.user:
        return

    await d_bot.process_commands(msg)

@d_bot.command(name='ping', help='- pong')
async def on_command_ping(ctx):
    if ctx.channel.id == config.get('chat_id_bot_commands'):
        await ctx.send('pong')
    else:
        await ctx.message.delete()
        await ctx.author.send('Please keep all commands to the "bot-commands" channel')

@d_bot.command(name='vote', help='- cast a vote for EL PRESIDENTE')
async def on_command_vote(ctx, cast_for : discord.Member = None):
    if ctx.channel.id == config.get('chat_id_bot_commands'):
        voter_id = str(ctx.author.id)# this must be cast to a string. the one read in from json will be interpreted as a string and if this is a num then 1 person can have 2 votes

        cur = data.get()['current_election']
        votes = cur['votes']

        if cast_for:
            cast_for_id = cast_for.id

            if cur['running']:

                if voter_id in votes:
                    await ctx.send('Vote updated!')
                else:
                    await ctx.send('Vote cast!')
                votes[voter_id] = {
                    "cast_for": cast_for_id
                }
                data.save()
            else:
                await ctx.send('No election is currently running')
        else:
            if cur['running']:
                if voter_id in votes:
                    await ctx.send(f'{ctx.author.mention}\'s current vote: {d_bot.guilds[0].get_member(votes[voter_id]["cast_for"]).display_name}')
                else:
                    await ctx.send(f'{ctx.author.mention}, you have yet to vote for someone')
                data.save()
            else:
                await ctx.send('No election is currently running')
    else:
        await ctx.message.delete()
        await ctx.author.send('Please keep all commands to the "bot-commands" channel')


@on_command_vote.error
async def on_error_vote(ctx, error):
    if isinstance(error, discord.ext.commands.BadArgument):
        await ctx.send('Could not recognize user')
    else:
        print('Command Vote Error:')
        print(error)
        await ctx.send('Internal error')

@d_bot.command(name='tally', help='- get a current tally of the votes')
async def on_command_tally(ctx):
    if ctx.channel.id == config.get('chat_id_bot_commands'):
        standing_str = "Standings:\n"
        template_str = "{:>5} - {:<}\n"
        for candidate in tally_election():
            print(candidate)
            standing_str += template_str.format(candidate[1], ctx.guild.get_member(int(candidate[0])).display_name)

        await ctx.send(standing_str)
    else:
        await ctx.message.delete()
        await ctx.author.send('Please keep all commands to the "bot-commands" channel')


@on_command_tally.error
async def on_error_tally(ctx, error):
    print('Command Tally Error:')
    print(error)
    await ctx.send('Internal error')

@d_bot.command(name='election', help='- view election information')
async def on_command_election(ctx):
    if ctx.channel.id == config.get('chat_id_bot_commands'):
        await ctx.send('Elections end every Saturday at 8PM EST. The victor is promoted to role EL PRESIDENTE. Term is 1 week.\nIf no votes are cast, EL PRESIDENTE shall remain in office for another term.\nIf there is a tie for EL PRESIDENTE, a random tied candidate shall be declared EL PRESIDENTE.')
    else:
        await ctx.message.delete()
        await ctx.author.send('Please keep all commands to the "bot-commands" channel')

def tally_election():
    tally = {}

    for vote in data.get()['current_election']['votes'].values():
        cast_for = vote['cast_for']
        if cast_for in tally:
            tally[cast_for] += 1
        else:
            tally[cast_for] = 1

    return sorted(tally.items(), key = lambda kv: kv[1], reverse = True)

@d_bot.command(name='clear_votes', help='- clears the votes')# TODO: permissions for this function should be admin only
@commands.has_permissions(administrator=True)
async def on_command_clear_votes(ctx):
    if ctx.channel.id == config.get('chat_id_bot_commands'):
        clear_votes()
        await ctx.send('Votes cleared!')
    else:
        await ctx.message.delete()
        await ctx.author.send('Please keep all commands to the "bot-commands" channel')

def clear_votes():
    try:
        data.get()['current_election']['votes'] = {}
        data.save()
    except Exception as e:
        print('Clear votes error:')
        print(e)

async def election_cycle():
    results = tally_election()
    general_chat = d_bot.guilds[0].get_channel(config.get('chat_id_general'))
    if len(results) > 0:
        top_candidate = results[0]

        tied = []

        #check for ties
        for candidate in results:
            if candidate[1] == top_candidate[1]: ## if this candidate got the same number of votes as the winner
                tied.append(candidate)

        if len(tied) > 1:
            await general_chat.send('A tie has occurred! Picking a random EL PRESIDENTE')
            top_candidate = random.choice(tied)# chaos

        print(f'Top: {top_candidate}')
        winner = d_bot.guilds[0].get_member(top_candidate[0])

        #remove current EL PRESIDENTE

        role_el_presidente = d_bot.guilds[0].get_role(config.get('role_id_el_presidente'))
        for m in role_el_presidente.members:
            await m.remove_roles(role_el_presidente)
            print(f'{m.display_name} is removed from EL PRESIDENTE')

        await winner.add_roles(role_el_presidente)
        print(f'{winner.display_name} is added to EL PRESIDENTE')

        data.get()['history'].append(winner.id)
        data.save()


        await general_chat.send(winner.mention + ' has been elected EL PRESIDENTE!!!')
    else:
        await general_chat.send('No votes. EL PRESIDENTE remains.')
    clear_votes()

async def election_coroutine():
    await d_bot.wait_until_ready()
    while not d_bot.is_closed():
        now = datetime.now()
        time = now.time()
        if now.weekday() == 5: #if now is Saturday
            if time.hour == 20: #if the hour is 8 pm
                if time.minute == 0: #if its 8:00pm
                    await election_cycle()

        sleep_time = 60 + (10 - time.second) ## this makes the sleep function stick around the 10-second mark for the next call
        await asyncio.sleep(sleep_time)

#load config
print(f'Loading config...')
if not config.load():
    print('Could not load config')
    quit()
print('\tDone')

#load election data
print(f'Loading election data...')
if not data.load():
    print('Could nto load election data')
    quit()
print('\tDone')

d_bot.loop.create_task(election_coroutine())
d_bot.run(config.get('discord_token'))
