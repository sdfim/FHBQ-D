<?php

$arr = [
"status",
"n 1 auto",
"n 2 auto",
"n 3 auto",
"n 1 on",
"n 2 on",
"n 3 on",
"n 1 off",
"n 2 off",
"n 3 off",
"ne 1 auto",
"ne 3 auto",
"ne 1 on",
"ne 3 on",
"ne 1 off",
"ne 3 off",
"ns 1 auto",
"ns 3 auto",
"ns 1 on",
"ns 3 on",
"ns 1 off",
"ns 3 off",
"s 1 auto",
"s 2 auto",
"s 3 auto",
"s 1 on",
"s 2 on",
"s 3 on",
"s 1 off",
"s 2 off",
"s 3 off",
"se 1 auto",
"se 3 auto",
"se 1 on",
"se 3 on",
"se 1 off",
"se 3 off",
"ss 1 auto",
"ss 3 auto",
"ss 1 on",
"ss 3 on",
"ss 1 off",
"ss 3 off",
"off"
];

/*
foreach ($arr as $val) {
	exec("python ch_command_v10_utf.py $val");
	sleep(1);
}
*/

exec("python ch_command_v10_utf.py n 1 off");
sleep(1);
exec("python ch_command_v10_utf.py off");
