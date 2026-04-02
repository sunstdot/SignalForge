import { NextResponse } from 'next/server';
import { getBriefingByDate } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const date = searchParams.get('date');

    if (!date) {
      return NextResponse.json(
        { error: 'Date parameter is required' },
        { status: 400 }
      );
    }

    // Validate date format (YYYY-MM-DD)
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(date)) {
      return NextResponse.json(
        { error: 'Invalid date format. Use YYYY-MM-DD' },
        { status: 400 }
      );
    }

    const briefing = getBriefingByDate(date);
    
    if (!briefing) {
      return NextResponse.json(
        { error: 'Briefing not found for this date' },
        { status: 404 }
      );
    }

    return NextResponse.json({ briefing });
  } catch (error) {
    console.error('Error fetching briefing:', error);
    return NextResponse.json(
      { error: 'Failed to fetch briefing' },
      { status: 500 }
    );
  }
}
