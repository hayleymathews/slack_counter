# slack_counter

slack bot to count stuff.   
if for example, someone says a phrase a lot in a meeting...


```
/counter [name(optional)]
if no name provided, lists all counters
if name given, displays details on counter

ex: /counter whee


/incr [name, value, hidden(optional)] 
increment counter with name by value 
if no counter exists, creates new one and starts count at value
if hidden - counter not be listed in /counter command unless the channel is a direct message

ex: /incr whee 1 hidden (creates hidden whee counter, with value of 1) 


/delete [name]
delete counter with name

ex: /delete whee
```
