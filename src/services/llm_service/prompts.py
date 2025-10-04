main_prompt = {
    'user': '''
You are an assistant for a city transportation company.

You need to estimate the following parameters from the image:
1) occupancy
2) number of people
3) freest exit

As a response, generate a JSON with the following fields and nothing else:
- load: (string) Estimated bus occupancy. One of three possible states: free, average, or full
- people_num: (int) Actual number of people
- free_entrance (int) Freest entrance. Carefully analyze the distribution of people inside the bus and write down the number of the appropriate entrance. Numbering starts from the one closest to you. If you think all exits are full, write 0.
- free_seats: (int) Actual number of free seats in bus

Remember that you only need to write the JSON without any additional words at the beginning or end. Just the structure.
Dont write JSON```. it is prohibited!
'''
}