import { NextRequest, NextResponse } from 'next/server';
import { RDSClient, StartDBInstanceCommand, StopDBInstanceCommand, DescribeDBInstancesCommand } from '@aws-sdk/client-rds';

const rds = new RDSClient({ region: process.env.AWS_REGION || 'eu-north-1' });
const DB_ID = 'trace-postgres-db';

export async function POST(req: NextRequest) {
    const { action } = await req.json();

    if (action === 'start') {
        await rds.send(new StartDBInstanceCommand({ DBInstanceIdentifier: DB_ID }));
        return NextResponse.json({ message: 'Database starting...' });
    }

    if (action === 'stop') {
        await rds.send(new StopDBInstanceCommand({ DBInstanceIdentifier: DB_ID }));
        return NextResponse.json({ message: 'Database stopped.' });
    }

    if (action === 'check') {
        const result = await rds.send(new DescribeDBInstancesCommand({ DBInstanceIdentifier: DB_ID }));
        const status = result.DBInstances?.[0]?.DBInstanceStatus;
        return NextResponse.json({ status });
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
}
