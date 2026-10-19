import * as migration_20261019_050827_initial from './20261019_050827_initial';

export const migrations = [
  {
    up: migration_20261019_050827_initial.up,
    down: migration_20261019_050827_initial.down,
    name: '20261019_050827_initial'
  },
];
