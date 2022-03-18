"use strict";
import {proj} from "../proj";

async function loop() {
    const poped = await proj.predis.blpop("queue", 5);
    const task_desc_s = poped[1];
    let task_desc;
    try {
        task_desc = JSON.parse(task_desc_s);
    } catch (e) {
        proj.logger.exception(e);
    }
    proj.logger.info("got task "+task_desc.func);
    const func = task_desc.func;
    const args = task_desc.args;
    if (typeof(proj.tasks[func])!="function") {
        console.log(`task ${func} not found`);
        process.exit(-1)
    }
    try {
        await ((this.tasks[func])(...args));
    } catch (e) {
        console.exception(e);
    }
}

export async function start() {
    while(true) {
        loop();
    }
}
