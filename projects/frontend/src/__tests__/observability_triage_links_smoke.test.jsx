import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';

describe('observability triage links smoke', () => {
  test('stats overview routes triage actions to help anchors and help page defines matching sections', () => {
    const statsOverviewPath = path.resolve(__dirname, '../components/Dashboard/StatsOverview.jsx');
    const helpPagePath = path.resolve(__dirname, '../components/Help/HelpPage.jsx');

    const statsOverviewSource = fs.readFileSync(statsOverviewPath, 'utf8');
    const helpPageSource = fs.readFileSync(helpPagePath, 'utf8');

    expect(statsOverviewSource).toContain("queue: '/help#queue-triage'");
    expect(statsOverviewSource).toContain("failures: '/help#failure-triage'");
    expect(statsOverviewSource).toContain("services: '/help#service-triage'");

    expect(helpPageSource).toContain('id="queue-triage"');
    expect(helpPageSource).toContain('id="failure-triage"');
    expect(helpPageSource).toContain('id="service-triage"');
  });
});
