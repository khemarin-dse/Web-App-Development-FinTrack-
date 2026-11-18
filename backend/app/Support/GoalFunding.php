<?php

namespace App\Support;

use App\Models\Transaction;
use Carbon\Carbon;
use Illuminate\Validation\ValidationException;

/**
 * Rules for moving money into a goal: it can only come from the remaining money
 * (income - expenses) of the CURRENT month — not from past or future months.
 */
class GoalFunding
{
    public static function availableThisMonth(int $userId): float
    {
        $now = now();

        $income = Transaction::where('user_id', $userId)->where('type', 'income')
            ->whereYear('date', $now->year)->whereMonth('date', $now->month)->sum('amount');

        $expense = Transaction::where('user_id', $userId)->where('type', 'expense')
            ->whereYear('date', $now->year)->whereMonth('date', $now->month)->sum('amount');

        return (float) ($income - $expense);
    }

    /** Throws a 422 validation error if this deposit breaks the rules. */
    public static function assertAllowed(int $userId, float $amount, string $date): void
    {
        $d = Carbon::parse($date)->startOfDay();

        if ($d->lt(now()->startOfMonth()) || $d->gt(now()->endOfDay())) {
            throw ValidationException::withMessages([
                'date' => ['Money for a goal can only come from this month (up to today). '
                         . 'Past and future months are not allowed.'],
            ]);
        }

        $available = self::availableThisMonth($userId);

        if ($amount > $available + 0.0001) {
            $msg = $available <= 0
                ? 'You have no remaining money this month to put into a goal.'
                : 'Not enough remaining money this month. Available: $' . number_format($available, 2) . '.';
            throw ValidationException::withMessages(['amount' => [$msg]]);
        }
    }
}
