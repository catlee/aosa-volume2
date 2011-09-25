A brief history
===============

GNU Mailman is free software for managing mailing lists.  Almost everybody who
writes or uses free and open source software has probably encountered a
mailing list.  Mailing lists can be discussion-based or announcement-based,
with all kinds of variations in between.  Sometimes mailing lists are
gatewayed to newsgroups on Usenet or Gmane.  Mailing lists typically have
archives which contain the historical record of all the messages that have
been posted to the mailing list.

GNU Mailman has been around since the early '90s, when John Viega wrote the
first version to connect fans with a band he was friends with in college: the
Dave Matthews Band.  By the mid-90's, the center of the Python universe had
moved from CWI in the Netherlands to CNRI in Reston Virginia USA, and we were
running its mailing list using Majordomo.  Of course, it just wouldn't do for
the Python world to be running a Perl-based mailing list, and besides, it was
too difficult to make the changes we needed to Majordomo.  Ken Manheimer was
instrumental in resurrecting an early version of Mailman from John's failed
hard drive.  Many excellent developers have contributed to Mailman since then,
and today, Mark Sapiro is maintaining the stable 2.1 branch, while I
concentrate on the new 3.0 version.

Many of the early architectural decisions John made have lived on in the code
right up until the Mailman 3 branch, and in fact can still be seen in the
stable branch.  Given that Mailman is at least 15 years old, this is a
testament to the good decisions John made originally, as well as to the
strengths of Python to allow us to evolve and improve some of the more fragile
parts of the system.  It also goes to show you how a vibrant community can
work around well-known limitations that can't be fixed with anything short of
a rewrite.  In the sections that follow, I touch on some of the more
problematic design decisions that have been (hopefully) fixed by the new
Mailman 3 code base.

In the early Mailman 1.x days, we had a lot of problems with messages getting
lost, or bugs causing messages to be re-delivered over and over again.  This
prompted us to articulate two overriding principles that I think were critical
to Mailman's ongoing success:

 * No message should ever get lost
 * No message should ever be delivered twice

In the Mailman 2.0 time frame, we really hammered on the architecture, and
specifically the design of the queue runner system, to ensure that these two
principles would always be of prime importance.  I'll talk about this system
later, but I do strongly feel that its delivery reliability, which has been
stable for at least a decade now, is one of the key reasons that Mailman is as
ubiquitous as it is today.  Despite the modernization to this subsystem in
Mailman 3, the design and implementation remains largely unchanged.


The anatomy of a message
========================

As you might guess, one of the core data structures in the system is the
*email message*.  In fact, many of the interfaces, functions, and methods in
the system take three arguments: the mailing list object, the message object,
and a metadata dictionary that is used to record and communicate state while a
message is processed through the system.

On the face of it, an email message is a simple object.  It consists of a
number of colon-separated key-value pairs, called the headers, followed by an
empty line which separates the headers from the message body.  You'd think
this type of textural representation would be easy to parse, generate, reason
about, and manipulate, but in fact you'd be wrong!  There are countless RFCs
that describe all the crazy variations that can occur, such as handling
complex data types like images, audio, and more.  Email can contain ASCII
English, or just about any language and character set in existence.  The basic
structure of an email message has been borrowed over and over again for other
protocols, such as NNTP and HTTP, yet each is slightly different.  Work on
Mailman has spawned several libraries just to deal with the vagaries of email,
and development is ongoing even today to fix and improve the email package in
the Python standard library so that it is more standards-compliant and robust.

Within Mailman, an email message is represented as a tree of connected message
objects, with a single message at the root.  Those of you poor souls
intimately familiar with the email-related RFCs, and in particular the MIME
standards, will know that a message can be a *multipart*, which is actually a
container object with various types and numbers of sub-message parts.  In
Mailman, we usually talk about this as the *message object tree*, and we pass
this tree around by reference to the root message object.

Mailman will almost always modify the original message in some way.
Sometimes, the transformations can be fairly benign, such as adding or
removing headers.  Sometimes, we'll completely change the structure of this
message object tree, such as when the content filter rips out certain content
types like HTML, images, or other non-text parts.  Mailman might even collapse
multipart/alternatives (i.e. where a message appears as both plain text and as
some rich text type), or add addition parts to contain information about the
mailing list itself.

As you'll see in the section about the queue system, we generally parse the
*on the wire* bytes representation of a message just once, when it first comes
into the system.  From then on, we deal only with the message object tree
until we're ready to send it back out to the outgoing mail server.  It's at
that point that we flatten the tree back to a bytes representation.  Along the
way, we might pickle the message object tree for quick storage to, and
reconstruction from, the file system.  *Pickles* are a Python technology for
serializing any Python object, including all its subobjects, and it's
perfectly suited to optimizing the handling of email message object trees.


The mailing list
================

As you've probably inferred, the *mailing list* is another core object in the
Mailman system.  Mailing list objects have undergone some radical redesigns in
Mailman 3, and I'll go into some details of that in a bit.  For now, it's
important to understand that most of the operations in Mailman are mailing
list-centric.  Here are some examples:

 * Membership is defined in terms of a user or address being subscribed to a
   specific mailing list.
 * Mailing lists have a large number of configuration options that are stored
   in the database, and which control everything from posting privileges, to
   how the message is modified before final delivery.
 * Mailing lists have owners and moderators which have greater permission to
   change aspects of the list, or to approve and reject questionable
   postings.
 * Every mailing list has its own archive.
 * Users post new messages to a specific mailing list.

and so on.  Almost every operation in Mailman takes a mailing list as an
argument, it's that fundamental.

One of John's earliest design decisions was how to represent a mailing list
object inside the system.  Naturally, he chose a Python class, with attributes
and methods to represent the configuration and operations of the mailing list.
In fact, he structured the code in a clever way: by using multiple
inheritance, each mixin class provided a related set of operations and
parameters.  This made it really easy to add entirely new functionality.  By
grafting on a new mixin class, the core ``MailList`` class could easily
accommodate something new and cool.
**[Will readers know what a mixin class is? - Amy]**

For example, in Mailman 2, when we wanted to add an auto-responder, we just
created a mixin to hold the data specific to that feature, and they would get
automatically initialized when a new mailing list was created.

This structure was even more useful when it came to the question of
persistence.  Obvious, we would have to somehow store the state of a mailing
list on disk to preserve it when Mailman was stopped and started.  Another of
John's early design decisions was to use pickles here too.  The ``MailList``'s
state was stored in a file called ``config.pck``, which was just the pickled
representation of the ``MailList``'s dictionary.  Every Python object has an
attribute dictionary called ``__dict__``.  Saving a mailing list object then
was just a matter of pickling its ``__dict__`` to a file, and loading it just
involved reading the pickle from the file and reconstituting its ``__dict__``.

Thus, when we added a new mixin class to implement some new functionality, all
the attributes of the mixin were automatically pickled and unpickled
appropriately.  The only extra work we had to do was to maintain a *schema
version number* to automatically upgrade older mailing list objects when new
features were added.

As cool as this was, both the mixin architecture and pickle persistence
eventually crumbled under their own weight.  Site administrators often
requested ways to access the mailing list configuration variables via
external, non-Python systems.  But the pickle protocol is entirely
Python-specific, so sequestering all that useful data inside a pickle wouldn't
work for them.  Also, because the entire state of a mailing list was contained
in the ``config.pck``, and Mailman has multiple processes that need to read,
modify, and write the mailing list state, we had to implement exclusive
file-based and NFS-safe locks to ensure data consistency.  Every time some
part of Mailman wants to change the state of a mailing list, it must acquire
the lock, write out the change, then release the lock.  This serialization of
operations on a mailing list turned out to be horribly slow and inefficient.

For these reason, Mailman 3 moved everything into a SQL database.  By default
SQLite3 is used, though this is easily changed, since Mailman 3 utilizes the
Object Relational Mapper called Storm, which supports a wide variety of
databases.

Another, bigger problem is that in Mailman 2, each mailing list is a silo.
Sometimes, we want to do operations across many mailing lists, or even all of
them.  For example, a user might want to temporarily suspend all their
subscriptions when they go on vacation.  Or a site administrator might want to
add some disclaimer to the welcome message of all of the mailing lists on her
system.  Even the simple matter of figuring out which mailing lists a single
address was subscribed to, required unpickling the state of every mailing list
on the system, since membership information was kept in the ``config.pck``
file too.

Another problem was that each ``config.pck`` file lived in a directory named
after the mailing list, but Mailman was originally designed without
consideration of virtual domains.  This lead to a very unfortunate problem
where two mailing lists could not have the same name in different domains.
For example, if you owned both the ``example.com`` and ``example.org``
domains, and you wanted them to act independently and allow for a different
``foo`` mailing list in each, you cannot do this in Mailman 2, without
modifications to the code, a barely-supported hook, or conventional
workarounds that forced a different list name under the covers.

This has been solved in Mailman 3 by changing the way mailing lists are
identified, along with moving all the data into a traditional database.
The *primary key* for the mailing list table is the *fully qualified list
name* or as you'd probably recognize it, the posting address.  Thus
``foo@example.com`` and ``foo@example.org`` are now completely independent
rows in the mailing list table, and can easily co-exist in a single Mailman
system.


Runners
=======

Messages flow through the system by way of a set of independent processes
called *runners*.  Originally conceived as a way of predictably processing all
the files found in a particular directory, there are now a few runners which
don't process files in a directory but instead are simply independent
processes that perform a specific task and are managed by a master runner.
More on that later.  When a runner does manage the files in a directory, we
sometimes call it a *queue runner*.

Mailman is religiously single threaded, even though there is significant
parallelism to exploit.  For example, we can be accepting messages from the
mail server at the same time we're sending messages out to recipients, or
processing bounces, or archiving a message.  Parallelism in Mailman is
achieved through the use of multiple processes, in the form of these runners.
For example, there is an *incoming* queue runner with the sole job of
accepting (or rejecting) messages from the upstream mail server.  There is an
outgoing queue runner with the sole job of communicating with the upstream
mail server over SMTP in order to send messages out to the final recipients.
There's an archiver queue runner, a bounce processing queue runner, a queue
runner for forwarding messages to an NNTP server, a queue runner for composing
digests, and several others.  Runners which don't manage a queue include an
LMTP runner and a REST HTTP runner.

Each queue runner is responsible for a single directory, i.e. its *queue*.
While the typical Mailman system can perform perfectly well with a single
process per queue, we use a clever algorithm for allowing parallelism within a
single queue directory, without requiring any kind of cooperation or locking.
The secret is in the way we name the files within the queue directory.

As mentioned above, every message that flows through the system is also
accompanied by a metadata dictionary that accumulates state and allows
independent components of Mailman to communicate with each other.  Python's
pickle library is able to serialize and deserialize multiple objects to a
single file, so we can pickle both the message object tree and metadata
dictionary into one file.

There is a core Mailman class called Switchboard which provides an interface
for enqueuing (i.e. writing) and dequeuing (i.e. reading) the message object
tree and metadata dictionary to files in a specific queue directory.  Every
queue directory has at least one switchboard instance, and every queue runner
instance has exactly one switchboard.

Pickle files all end in the ``.pck`` suffix, though you may also see ``.bak``,
``.tmp``, and ``.psv`` files in a queue.  These are used to ensure one of the
two sacrosanct tenets of Mailman: no file should ever get lost, and no message
should ever be delivered twice.  But things usually work properly and these
files can be pretty rare.

For really busy sites, Mailman supports running more than one runner process
per queue directory, completely in parallel, with no communication between
them or locking necessary to process the files.  It does this by naming the
pickle files with a SHA1 hash, and then allowing a single queue runner to
manage just a slice of the hash space.  So if you want to run two runners on
the ``bounces`` queue, one would only process files from the top half of the
hash space, and the other would only process files from the bottom half of the
hash space.  The hashes are calculated using the contents of the pickled
message object tree, plus the name of the mailing list that the message is
destined for, plus a time stamp.  This makes the SHA1 hash effectively random,
and thus on average a two-runner queue directory will have about equal amounts
of work per process.  And because the hash space can be statically divided,
these processes can operate on the same queue directory with no interference
or communication necessary.

You might have noticed that there's an interesting limitation to this
algorithm: the number of runners per queue directory must be a power of 2.
So, you can run 1, 2, 4, or 8 processes, but not for example, 5.  In practice
this has never been a problem, since in practice few sites will ever need more
than 4 processes to handle their load.

There's another side effect of this algorithm that did hurt us during the
early design of this system.  It turns out to be really important to process
queue files in FIFO order.  That's because, despite the unpredictability of
email delivery, you'd like that replies to a mailing list get sent out in
roughly chronological order.  Not making your best attempt at doing so can
cause even greater confusion to members.  But using SHA1 hashes as file names
obliterates any timestamps, and for performance reasons you do not want to do
a stat(2) of the file or have to unpickle the contents (e.g. to read a time
stamp in the metadata) before you can sort the messages for processing.

Our solution to this was to extend the file naming algorithm to include a time
stamp prefix, as the number of seconds since the epoch.  Thus our files are
named ``<timestamp>+<sha1hash>.pck``.  So, each loop through the queue runner
only needs to do an ``os.listdir()`` to get all the files waiting to be
processed, then split the file name and ignore any where the SHA1 hash doesn't
match its slice of responsibility, then sort the files based on the timestamp
part of the file name.

In practice this has worked extremely well for at least a decade, with only
the occasional minor bug fix or elaboration to handle obscure corner cases and
failure modes.  It's one of the most stable parts of Mailman and was largely
ported untouched from Mailman 2 to Mailman 3.


The master queue runner
=======================

"One process to rule them all."

With all these runner processes, we needed a simple way to start and stop them
consistently.  Thus the master runner process was born, and it must be able to
handle both queue runners, and runners which do not manage a queue.  For
example, in Mailman 3, we accept messages from the incoming upstream mail
server via LMTP, which is a protocol similar to SMTP, but which operates only
for local delivery and thus can be much simpler, as it doesn't need to deal
with the vagaries of delivering mail over the wild and crazy unpredictable
internet.  The LMTP runner simply listens on a port, waiting for its upstream
mail server to connect and send it some message bytes.  It then parses this
byte stream into a message object tree, creates an initial metadata dictionary
and enqueues this into a processing queue directory.

We also have a runner that listens on another port and processes REST requests
over HTTP.  More on this later, but this process doesn't actually touch any
files on disk at all.

Still, a typical running Mailman system might have 8 or 10 processes, and they
all need to be stopped and started appropriately and conveniently.  They can
also crash occasionally, for example when a bug in Mailman causes an exception
to occur that isn't caught.  In cases like this, the master will restart the
runner process, and because of the "never lose a message" and "never deliver a
message twice" mantras, it will generally just pick up where it left off.

When the master watcher starts, it looks in a configuration file to determine
how many and which types of child runners to start.  For the LMTP and REST
runners, there is usually exactly one such process.  For the queue runners, as
mentioned above, there can be a power-of-2 number of parallel processes.  The
master forks and execs all the runner processes based on the configuration
file, passing in the appropriate command line arguments for each (e.g. to tell
the subprocess which slice of the hash space to look at).  Then the master
basically sits in an infinite loop, blocking until one of its child processes
exits.  It keeps track of the process ID for each child, along with a count of
the number of times the child has been restarted.  This latter is to prevent a
catastrophic bug from causing a cascade of unstoppable restarts.  There's a
configuration variable which specifies how many restarts are allowed, after
which an error is logged and the runner is not restarted.

When a child does exit, the master looks at both the exit code and the signal
that killed the subprocess.  Each runner process installs a number of signal
handlers with the following semantics:

 * SIGTERM - intentionally stop the subprocess.  It is not restarted.  SIGTERM
   is what ``init`` will kill the process with when changing run levels, and
   it's also the signal that Mailman itself uses to stop the subprocess.
 * SIGINT - also used to intentionally stop the subprocess, it's the signal
   that occurs when *control-C* is used in a shell.  The runner is not
   restarted.
 * SIGHUP - tells the process to close and reopen their log files, but to keep
   running.  This is used when rotating log files.
 * SIGUSR1 - initially stop the subprocess, but allow the master to restart
   the process.  This is used in the ``restart`` command of init scripts.

The master also installs handlers for all four of these signals, but it
doesn't do much more than forward them to all its subprocesses.  So if you
sent SIGTERM to the master, all the subprocesses would get SIGTERM'd and
exit.  The master would know that the subprocess exited because of SIGTERM and
it would know that this was an intentional stoppage, so it would not restart
the runner.

The master installs one other signal handler, on SIGALRM.  It does this
because the master acquires a file lock with a lifetime of about a day and a
half, to ensure that only one master is running at any one time.  Multiple
masters would really screw things up!  Just to be safe though, the master
wakes up about once a day and refreshes this file lock.  So the lock should
never time out or be broken while Mailman is running, unless of course your
system crashes, or the master is killed with an uncatchable signal.  In those
cases, the command line interface to the master process provides a switch to
override a stale lock.

This leads me to the last bit of the master watcher story, the command line
interface to it.  The actual master script takes very few command line
options.  Both it and the queue runner scripts are intentionally kept simple.
This wasn't the case in Mailman 2, where the master script was fairly complex
and tried to do too much.  This made it more difficult to understand and
debug.  In Mailman 3, the real CLI for the master process is in the
``bin/mailman`` script, a kind of uber-script that contains a number of
subcommands, in a style made popular by programs like Subversion.  This is
nice because you only have a few programs that need to be installed on your
shell's ``PATH``.  ``bin/mailman`` has subcommands to start, stop, and restart
the master, as well as all the subprocesses, and also to cause all the log
files to be reopened.  The ``start`` subcommand forks and execs the master
process, while the others simply send the appropriate signal to the master,
which then propagates it to its subprocesses as described above.

This improved separation of responsibility make it much easier to understand
each individual piece.


Rules, links, and chains
========================

A mailing list posting goes through several phases from the time it's first
received, until the time it's sent out to the list's membership.  In Mailman
2, each processing step was represented by a *handler*, and a string of
handlers were put together into a *pipeline*.  So, when a message came into
the system, Mailman would first determine which pipeline would be used to
process it, and then each handler in the pipeline would be called in turn.
Some handlers would do moderation functions (i.e. "is this person allowed to
post to the mailing list?"), others would do modification functions
(i.e. "which headers should I remove and add?"), and others would copy the
message to other queues.  A few examples of the latter are:

 * A message accepted for posting would be copied to the *archiver* queue at
   some point, so that its queue runner would add the message to the archive.
 * A copy of the message eventually had to end up in the *outgoing* queue so
   that it could be delivered to the upstream mail server, which has the
   ultimate responsibility of delivery to a list member.
 * A copy of the message had to get put into a digest for people who wanted
   only occasional, regular traffic from the list, rather than an individual
   message whenever someone sent it.

The pipeline-of-handlers architecture proved to be quite powerful.  It
provided an easy way that people could extend and modify Mailman to do custom
operations.  The interface for a handler was fairly straightforward, and it
was a simple matter to implement a new handler, ensuring it got added to the
right pipeline in the right location to accomplish the custom operation.

One problem with this though was that mixing moderation and modification in
the same pipeline became problematic.  The handlers had to be sequenced in the
pipeline just so, or unpredictable or undesirable things would happen.
Sometimes, you might just want to moderate the message without modifying it,
or vice versa.  So in Mailman 3, we've split these two operations into
separate subsystems.

In Mailman 3, the LMTP runner parses the messages bytes into a message object
tree and creates an initial metadata dictionary for the message.  It then
enqueues these to one or another queue directory.  Some messages may be *email
commands* (e.g. to join or leave a mailing list, to get automated help, etc.)
which are handled by a separate queue.  Most messages are postings to the
mailing list, and these get put in the *incoming* queue.  The incoming queue
runner processes each message sequentially through a *chain* consisting of any
number of *links*.  There is a built-in chain that most mailing lists use, but
even this is configurable.

Each link in the chain contains three pieces of information: a rule name, an
action, and a parameter for the action.  *Rules* are simple pieces of code
which gets passed the typical three parameters, the mailing list, the message
object, and the metadata dictionary.  Rules are not supposed to modify the
message, and make and return just a binary decision.  Did the rule match or
not?  There are rules for recognizing pre-approved postings, for catching mail
loops, and for recognizing various conditions which allow or disallow a
posting.  It's important to note that the rule itself does not dispose of a
disallowed posting, it just indicates whether the condition to disallow it
matched or not.  Each rule that matches gets added to a list in the metadata
dictionary, and each rule that misses gets added to a different list.  That
way, later on, Mailman will know exactly which rules matched and which ones
missed.

The central chain-processing loop then calls each rule in turn, and if the
rule matches, it executes the chain link's action.  Most links defer action
until later, which has the effect of grouping the moderation rules together, so
that every cause for discarding a message can be recorded.  Actions can also
*jump* to another chain, and there are chains which discard, reject
(i.e. bounce back to the original author), and accept messages, as well as
hold them for manual moderation.  Thus accepting a message is implemented in
the chain as a jump to the standard *accept* chain.

A special action called *detour* can also be taken.  You can think of a detour
as suspending the processing of the current chain, pushing its state on a
stack, and jumping to a new chain.  When that new chain is exhausted, the old
chain is popped off the stack and resumed at the next link.  Detours are
currently only used to process a message through dynamically created chains,
such as those that match header values based on database or configuration file
entries.

Because chains and rules are extensible and customizable, just about any
processing pipeline you can imagine can be implemented.


Handlers and pipelines
======================

Let's say that once a message as made its way through the chains and rules,
Mailman has determined that it can be posted to the mailing list.  Every
subscribed member will get a copy of the message, but Mailman must first
modify the message to meet its standards.  For example, some headers may get
added or deleted, and some messages may get some extra decorations that
provide useful information, such as how to leave the mailing list.  These
modifications are performed by a *pipeline* which contains a sequence of
*handlers*.  In a manner similar to chains and rules, pipelines and handlers
are extensible, but there are a number of built-in pipelines for the common
cases.  Handlers have a similar interface as rules, accepting a mailing list,
message object, and metadata dictionary.  However unlike rules, handlers can
and do modify the message.

For example, a posted message needs to have a ``Precedence:`` header added
which tells other automated software that this message came from a mailing
list.  This header is a defacto standard to prevent e.g. vacation programs
from responding back to the mailing list.  Adding this header (among other
header modifications) is done by the ``cook-headers`` handler.  Unlike with
rules, handler order generally doesn't matter, although enqueuing the message
to the outgoing, archiver, digest, and NNTP queue runners also happens via
handlers, so these usually appear at the end of the pipeline.


VERP
====

*VERP* stands for *Variable Envelope Return Path*, and it is a well-known
technique that mailing lists can use to unambiguously determine recipient
addresses which bounce.  When an address on a mailing list is no longer
active, the recipient's mail server will bounce the message.  In the case of a
mailing list, you want this bounce to go back to the mailing list, not to the
original author of the message.  The author can't do anything about the
bounce, and worse, sending the bounce back to the author can leak information
about who is subscribed to the mailing list.  When the mailing list gets the
bounce, it can does something useful, such as disable the bouncing address or
remove it from the list's membership.

There are two general problems with this.  First, even though there is a
standard format for these bounces (called "delivery status notifications")
many mail servers out there do not conform to it.  Instead, the body of their
bounce messages can contain just about any amount of
difficult-to-machine-parse gobbledygook, and of course you really want to
automate the process of bounce detection.  In fact, Mailman uses a library
that contains dozens of bounce format heuristics, which at least do better
than nothing.

Second, imagine the situation where a member of a mailing list has several
forwards.  She might be subscribed to the list with her anne@example.com
address, but this might forward to person@example.org which might further
forward the message to me@example.net.  When the server at example.net gets
the message at the final destination, it will usually just send a bounce
saying that me@example.net is no longer valid.  But the Mailman server that
sent the message only knows the member as anne@example.com, so the bounce
flagging me@example.net will not contain a subscribed address, and will just
get discarded.

Along comes VERP, which exploits a requirement of the fundamental SMTP
protocol to provide unambiguous bounce detection, by returning such bounce
messages to the *envelope sender*.  This is not the ``From:`` field in the
message body, but in fact the ``MAIL FROM`` value during the SMTP dialog.
This is preserved along the delivery route, and the ultimate receiving mail
server is required by the protocol to send the bounces to this address.  We
can use this fact to encode the original recipient email address into the
``MAIL FROM`` value.

For example, let's say that the recipient is anne@example.com and the Mailman
server is mylist@example.org.  The envelope sender for a mailing list posting
sent to anne@example.com will be mylist-bounce+anne=example.com@example.org.
The ``+`` here is a local address separator, which is a format supported by
most modern mail servers.  So when the bounce comes back, it will actually get
delivered to ``mylist-bounce@example.com`` but with the ``To:`` header still
set to the encoded recipient address.  Mailman can then parse this ``To:``
header to decode the original recipient, e.g. anne@example.com.

While VERP is an extremely powerful tool for culling bad addresses from the
mailing list, it does have one potentially important disadvantage.  Using VERP
requires that Mailman send out exactly one copy of the message per recipient.
Without VERP, Mailman can bundle up identical copies of an outgoing message
for multiple recipients, thus reducing overall bandwidth and processing time.
But VERP requires a unique ``MAIL FROM`` for each recipient, and the only way
to do that is to send a unique copy of the message.  Generally this is an
acceptable trade-off, and in fact, once these individualized messages are
being sent for VERP anyway, there are a lot of useful things Mailman can also
do.  For example, it can embed a URL in the footer of the message customized
for each recipient which gives them a direct link to unsubscribe from the
list.  You could even imagine various types of *mail-merge* operations for
customizing the body of the message for each individual recipient.


REST
====

One of the key architectural changes in Mailman 3 addresses a common request
over the years: allow Mailman to be more easily integrated with external
systems.  When I was hired by Canonical in 2007, my job was originally to add
mailing lists to Launchpad.  I knew that Mailman 2 could do the job, but we
had the pesky problem that the web ui would have to be thrown away because we
did not want to expose Mailman's ancient circa-1996 user interface to users.
Since Launchpad mailing lists were almost always going to be discussion lists,
we wanted very little variability in the way they operated.  List
administrators would not need the plethora of options available in the typical
Mailman site, and what few options they would need could be specified through
the Launchpad web ui.

At the time, Launchpad was not open source, so we had to design the integration
in such a way that Mailman 2's GPLv2 code could not infect Launchpad.  This
led to a number of architectural decision during that integration design that
were quite tricky and somewhat inefficient.  Because Launchpad is now open
source, these hacks wouldn't be necessary today, but having to do it this way
did provide some very valuable lessons on how a web ui-less Mailman could be
integrated with external systems.  The vision I started to form was of a core
engine that implemented mailing list operations efficiently and reliably, and
that could be managed by any kind of web front-end, including ones written in
Zope, Django, even non-Python frameworks such as PHP, or with no web ui at
all.

There were a number of technologies at the time that would allow this, and in
fact Mailman's integration with Launchpad is based on XMLRPC.  But XMLRPC has
a number of problems that make it a less than ideal protocol.

A year or so after mailing lists became operational in Launchpad, we hired
Leonard Richardson to design and implement an API for Launchpad so that it too
could be managed, controlled, and queried without the use of the web ui.
Leonard is an expert on REST (Representational State Transfer) defined by Roy
Fielding in 2000, but only really becoming widely known years later.  Leonard
had written the definitive O'Reilly book on REST, and was instrumental in
teaching the Launchpad team the techniques and principles behind it.  He was
one of the key architects and developers behind Launchpad's adoption of REST,
but all the Launchpad developers at the time began exposing bits of Launchpad
in the API.

I drank the Kool-aid and became a big fan.  I soon realized that this was the
perfect fit for Mailman 3 and began building an infrastructure for exposing
Mailman's functionality though a REST API.

One problem was finding an appropriate toolkit to do this with.  It's not a
particular goal of mine to implement all the HTTP bits and pieces, along with
the dispatcher, response code, and object representation encoding necessary to
make this work.  Fortunately Leonard and the other Launchpad developers had
written a nice GPL-compatible library to hook Zope interfaces up to an API
almost automatically.  I began using this library and had some initial
successes.  But I soon ran into several roadblocks which caused me to abandon
this library.  The primary reason was that, even though Mailman heavily uses
Zope interfaces internally, it's not at all a Zope application the way
Launchpad was.  Leonard's library worked beautifully for Zope applications,
but it was unwieldy and much too heavyweight for a non-Zope application like
Mailman.

It was about this time that I attended a Python conference where a talk on
``restish.io`` was given.  This seemed like exactly the kind of lightweight
toolkit I needed, and indeed it was effortless (and kind of joyful) to rip
out all the old REST stuff and re-implement it on top of restish.io.  Now, it
takes me just minutes to expose some new functionality over REST.

I'm convinced this is a powerful paradigm that more applications should
adopt.  A core engine that implements its basic functionality well, with a
REST API used to query and control it, is an architecture that is extremely
flexible and can be used and integrated in ways that are beyond the initial
vision of the system designers.  I'm excited when I hear how people want to
use Mailman 3 in ways I didn't imagine, and I think "yes, you can do that via
the REST API".

Not only does this design allow for much greater choices for deployment, even
the official components of the system can be designed and implemented
independently.  For example, the new official web ui for Mailman 3 is
technically a separate project with its own codebase, and in fact while I help
inform its direction, I can leave the creation of it to much more talented web
designers.  These outstanding developers are empowered to make decisions,
create designs, and execute implementations without my being a bottleneck, or
(hopefully!) a hindrance.  The web ui can feed back into the core engine
implementation by requesting additional functionality, exposed through the
REST API, but they needn't wait for it, since they can mock up the server side
on their end and continue experimenting and developing the web ui.  Once the
core engine catches up, they can hook it all together and watch it work for
real.

We plan to use the REST API for many more things, including allowing the
scripting of common operations, and even integration with IMAP or NNTP servers
for alternative access to the archives.


Lessons
=======

Well, I've pretty much ran out of time, and there are lots of other
interesting architectural decisions in Mailman which I can't cover.  These
include the configuration subsystem, the testing infrastructure, the database
layer, the use of interfaces, archiving, mailing list styles, the email
commands and command line interface, internationalization, and integration
with the outgoing mail server.  Contact us on the developers mailing list and
I'm happy to go into more detail.

To wrap up, here are some lessons I've learned while rewriting a popular,
established, and stable piece of the open source ecosystem.

* Use test driven development (TDD).  There really is no other way!  Mailman 2
  largely lacks an automated test suite, and while it's true that not all of
  the Mailman 3 code base is covered by its test suite, most of it is, and all
  new code is required to be accompanied by tests, using either unittests or
  doctests.  Doing TDD is the only way to give you confidence that the changes
  you make today do not introduce regressions in existing code.  Yes, TDD can
  sometimes take longer, but think of it as an investment in the future
  quality of your code.  In that way, *not* having a good test suite means
  you're just wasting your time.  Remember the mantra: untested code is broken
  code. 

* Get your bytes/strings story straight from the beginning.  In Python 3, a
  sharp distinction is made between unicode text strings and byte arrays,
  which, while initially painful, is a huge benefit to writing correct code.
  Python 2 blurred this line by having unicodes and 8-bit strings, with some
  automated coercions between them.  While appearing to be a useful
  convenience, problems with this fuzzy line is the number one cause of bugs
  in Mailman 2.  This is not helped by the fact that email is notoriously
  difficult to classify between strings and bytes.  Technically, the
  on-the-wire representation of an email is as a sequence of bytes, but these
  bytes are almost always ASCII, and there is a strong temptation to
  manipulate message components as text.  The email standards themselves
  describe how human readable, non-ASCII text can be safely encoded, so even
  things like finding a ``Re:`` prefix in a ``Subject:`` header will be text
  operations, not byte operations.  Mailman's principle is to convert all text
  to unicode as early as possible, deal with the text as unicode internally,
  and only convert it back to bytes on the way out.  It's critical to be clear
  in your mind right from the start when you're dealing with bytes and when
  you're dealing with text (unicode), since it's very difficult to retrofit
  this fundamental model shift later.

* Internationalize your application from the start.  Do you want your
  application to only be used by the minority of the world that speaks English?
  Think about how many fantastic users this ignores!  It's not hard to
  set up internationalization, and Python provides lots of good tools for
  making this easy, many of which were pioneered in Mailman.  I've even spun
  off some higher level libraries that provide a very nice API for
  internationalization.  Don't worry about the translations to start with, if
  your application is accessible to the world's wealth of languages, you will
  have volunteer translators knocking down your door to help.

GNU Mailman is a vibrant project with a healthy user base, and lots
of opportunities for contributions.  Here are some resources you can use if
you think you'd like to help us out, which I hope you do!

Primary web site        : http://www.list.org
Project wiki            : http://wiki.list.org
Developer mailing list  : mailman-developers@python.org
Users mailing list      : mailman-users@python.org
Freenode IRC channel    : #mailman