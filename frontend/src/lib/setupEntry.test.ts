import test from 'node:test';
import assert from 'node:assert/strict';
import {initialView} from './setupEntry';
test('first use opens setup; completed setup opens live; explicit links stay usable',()=>{
 assert.equal(initialView('',false),'preferences');
 assert.equal(initialView('',true),'live');
 assert.equal(initialView('?view=preferences',true),'preferences');
 assert.equal(initialView('?view=log',false),'log');
 assert.equal(initialView('?view=live',false),'live');
 assert.equal(initialView('?view=unexpected',false),'preferences');
});
