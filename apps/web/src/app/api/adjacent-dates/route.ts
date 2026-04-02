import { NextResponse } from 'next/server';
import { getAdjacentDates } from '@/lib/db';

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

    const adjacent = getAdjacentDates(date);
    return NextResponse.json(adjacent);
  } catch (error) {
    console.error('Error fetching adjacent dates:', error);
    return NextResponse.json(
      { error: 'Failed to fetch adjacent dates' },
      { status: 500 }
    );
  }
}
