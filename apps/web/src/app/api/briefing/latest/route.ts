import { NextResponse } from 'next/server';
import { getLatestBriefing } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const briefing = getLatestBriefing();
    
    if (!briefing) {
      return NextResponse.json(
        { error: 'No briefing found' },
        { status: 404 }
      );
    }

    return NextResponse.json({ briefing });
  } catch (error) {
    console.error('Error fetching latest briefing:', error);
    return NextResponse.json(
      { error: 'Failed to fetch briefing' },
      { status: 500 }
    );
  }
}
